import uuid
from decimal import Decimal

from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from products.models import Product, ProductVariant
from django.utils import timezone

# Custom manager to exclude soft-deleted orders by default
class ActiveOrderManager(models.Manager):
	"""Manager that excludes soft-deleted orders."""
	def get_queryset(self):
		return super().get_queryset().filter(is_deleted=False)

class AllOrderManager(models.Manager):
	"""Manager that includes all orders (including deleted ones)."""
	pass

class Cart(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
	session_key = models.CharField(max_length=40, blank=True, null=True, db_index=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		if self.user:
			return f"Cart for {self.user.username}"
		return f"Cart for session {self.session_key}"

	def total_items(self):
		return sum(item.quantity for item in self.items.all())

	def total_price(self):
		return sum(item.subtotal() for item in self.items.all())

	class Meta:
		indexes = [
			models.Index(fields=['user'], name='cart_user_idx'),
		]

class CartItem(models.Model):
	cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
	product = models.ForeignKey(Product, on_delete=models.CASCADE)
	variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
	quantity = models.PositiveIntegerField(default=1)
	price = models.DecimalField(max_digits=10, decimal_places=2)
	added_at = models.DateTimeField(auto_now_add=True)

	def subtotal(self):
		return self.quantity * self.price

	def __str__(self):
		return f"{self.quantity} x {self.product.name}"

	class Meta:
		indexes = [
			models.Index(fields=['cart', 'product'], name='cartitem_cart_product_idx'),
		]

class Order(models.Model):
	STATUS_CHOICES = (
		('Pending', 'Pending'),
		('Processing', 'Processing'),
		('Shipped', 'Shipped'),
		('Delivered', 'Delivered'),
		('Completed', 'Completed'),
		('Cancelled', 'Cancelled'),
	)

	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
	full_name = models.CharField(max_length=100)
	phone = models.CharField(max_length=20)
	email = models.EmailField(blank=True)
	delivery_address = models.TextField()
	delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
	delivery_option = models.CharField(max_length=10, choices=(('24h', '24-hour'), ('2d', '2-day')), default='2d')
	total = models.DecimalField(max_digits=10, decimal_places=2)
	payment_method = models.CharField(max_length=50, blank=True, null=True, help_text='Selected payment method for this order (paystack, manual, pay_on_delivery)')
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
	notes = models.TextField(blank=True, default='')
	receipt = models.FileField(
		upload_to='receipts/', 
		blank=True, 
		null=True, 
		validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
		help_text='Upload payment receipt (PDF or image only, max 5MB)'
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	# Timestamps for fulfillment — set when status transitions occur
	shipped_at = models.DateTimeField(null=True, blank=True, help_text='When the order was marked shipped')
	delivered_at = models.DateTimeField(null=True, blank=True, help_text='When the order was marked delivered')

	tracking_number = models.CharField(max_length=100, blank=True, null=True, db_index=True, help_text='Carrier tracking number for this order')
	number = models.CharField(max_length=30, unique=True, blank=True, help_text='Human-friendly order number (e.g. EST-2026-0001)')

	# Soft delete fields
	is_deleted = models.BooleanField(default=False, db_index=True)
	deleted_at = models.DateTimeField(null=True, blank=True)

	confirmation_token = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True, help_text='Token for public order confirmation page access')

	# Sample data flag
	is_sample = models.BooleanField(default=False, db_index=True, help_text='Marks orders created by the sample data tool')

	# Custom managers
	objects = ActiveOrderManager()  # Default manager (excludes deleted)
	all_objects = AllOrderManager()  # Includes deleted orders

	class Meta:
		ordering = ['-created_at']
		indexes = [
			models.Index(fields=['user', '-created_at'], name='order_user_created'),
			models.Index(fields=['status'], name='order_status'),
			models.Index(fields=['-created_at'], name='order_created_desc'),
			models.Index(fields=['status', '-created_at'], name='order_status_created'),
			models.Index(fields=['is_deleted', '-created_at'], name='order_deleted_created'),
		]

	def __str__(self):
		return f"Order #{self.number or self.id} - {self.full_name}"

	def _generate_order_number(self):
		from django.utils import timezone
		import random
		import string
		year = timezone.now().year
		prefix = f"EST-{year}-"
		# Find the highest existing order number for this year
		existing = Order.objects.filter(number__startswith=prefix).order_by('-number').first()
		if existing and existing.number:
			try:
				seq = int(existing.number.split('-')[-1]) + 1
			except (ValueError, IndexError):
				seq = 1
		else:
			seq = 1
		return f"{prefix}{seq:04d}"

	def save(self, *args, **kwargs):
		if not self.number:
			self.number = self._generate_order_number()
			# Handle race condition: retry if number already exists
			while Order.objects.filter(number=self.number).exists():
				self.number = self._generate_order_number()
		super().save(*args, **kwargs)
	
	def grand_total(self):
		"""Calculate grand total (subtotal + delivery fee)"""
		from decimal import Decimal
		total = self.total if isinstance(self.total, Decimal) else Decimal(str(self.total))
		delivery_fee = self.delivery_fee if isinstance(self.delivery_fee, Decimal) else Decimal(str(self.delivery_fee))
		return total + delivery_fee

	def soft_delete(self):
		"""Mark order as deleted without removing from database and reverse stock."""
		from .utils import reverse_order_stock
		
		# Reverse stock before marking as deleted
		reverse_order_stock(self)
		
		# Mark as deleted
		self.is_deleted = True
		self.deleted_at = timezone.now()
		self.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])

class OrderItem(models.Model):
	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
	product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
	variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
	quantity = models.PositiveIntegerField(default=1)
	price = models.DecimalField(max_digits=10, decimal_places=2)
	is_sample = models.BooleanField(default=False, help_text='Marks order items created by the sample data tool')

	def subtotal(self):
		return self.quantity * self.price

	def __str__(self):
		return f"{self.quantity} x {self.product.name}"

class PaymentTransaction(models.Model):
	"""Record external payment transactions (Paystack) for audit and idempotency."""
	reference = models.CharField(max_length=255, unique=True)
	order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
	amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
	currency = models.CharField(max_length=10, default='NGN')
	status = models.CharField(max_length=50, blank=True)
	payment_method = models.CharField(max_length=50, blank=True, null=True, help_text='Payment channel: card, bank, ussd, qr, etc.')
	raw_response = models.JSONField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	is_sample = models.BooleanField(default=False, help_text='Marks payment transactions created by the sample data tool')

	def __str__(self):
		return f"Paystack {self.reference} ({self.status})"

class WebhookEvent(models.Model):
	"""Store raw webhook events for reliable processing and retries."""
	provider = models.CharField(max_length=50, default='paystack')
	event_type = models.CharField(max_length=100)
	reference = models.CharField(max_length=255, blank=True, null=True)
	payload = models.JSONField()
	headers = models.JSONField(null=True, blank=True)
	processed = models.BooleanField(default=False)
	attempts = models.IntegerField(default=0)
	last_attempt = models.DateTimeField(null=True, blank=True)
	response_text = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	processed_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"Webhook {self.provider}:{self.event_type} ref={self.reference} processed={self.processed}"

class OrderAuditLog(models.Model):
	"""Audit log for tracking order changes, including stock reversals."""
	ACTION_CHOICES = (
		('cancel', 'Cancelled'),
		('delete', 'Deleted'),
		('status_change', 'Status Changed'),
		('stock_reversal', 'Stock Reversal'),
		('update', 'Updated'),
	)
	
	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='audit_logs')
	action = models.CharField(max_length=20, choices=ACTION_CHOICES)
	changes = models.JSONField(default=dict, blank=True, help_text='Dict of field changes with [old_value, new_value]')
	stock_reversed = models.JSONField(default=dict, blank=True, help_text='Stock reversals: {product_id: qty, variant_id: qty}')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']
		indexes = [
			models.Index(fields=['order', '-created_at'], name='orderaudit_order_created'),
		]

	def __str__(self):
		return f"Order {self.order.id} - {self.action} at {self.created_at}"

class CheckoutSettings(models.Model):
    delivery_fee_24h = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Delivery fee for 24-hour delivery")
    delivery_fee_2d = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Delivery fee for 2-day delivery")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Checkout Settings"

    class Meta:
        verbose_name = "Checkout Setting"
        verbose_name_plural = "Checkout Settings"

class PaymentSettings(models.Model):
    enable_paystack = models.BooleanField(default=True, help_text='Allow Paystack checkout when the public key is configured.')
    enable_manual_transfer = models.BooleanField(default=True, help_text='Allow manual bank transfer checkout.')
    enable_pay_on_delivery = models.BooleanField(default=False, help_text='Allow pay-on-delivery checkout option.')
    pay_on_delivery_max = models.DecimalField(max_digits=12, decimal_places=2, default=100000.00, help_text='Maximum order total eligible for pay on delivery.')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Payment Settings"

    class Meta:
        verbose_name = "Payment Setting"
        verbose_name_plural = "Payment Settings"

