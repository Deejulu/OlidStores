from django.db import models
from django.conf import settings
from products.models import Product, ProductVariant

class Cart(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
	session_key = models.CharField(max_length=40, blank=True, null=True)
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
	delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
	delivery_option = models.CharField(max_length=10, choices=(('24h', '24-hour'), ('2d', '2-day')), default='2d')
	total = models.DecimalField(max_digits=10, decimal_places=2)
	payment_method = models.CharField(max_length=50, blank=True, null=True, help_text='Selected payment method for this order (paystack, manual, pay_on_delivery)')
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
	notes = models.TextField(blank=True, default='')
	receipt = models.FileField(upload_to='receipts/', blank=True, null=True, help_text='Upload payment receipt for manual bank transfer')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	# Timestamps for fulfillment — set when status transitions occur
	shipped_at = models.DateTimeField(null=True, blank=True, help_text='When the order was marked shipped')
	delivered_at = models.DateTimeField(null=True, blank=True, help_text='When the order was marked delivered')

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"Order #{self.id} - {self.full_name}"
	
	def grand_total(self):
		"""Calculate grand total (subtotal + delivery fee)"""
		return self.total + self.delivery_fee

class OrderItem(models.Model):
	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
	product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
	variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
	quantity = models.PositiveIntegerField(default=1)
	price = models.DecimalField(max_digits=10, decimal_places=2)

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

