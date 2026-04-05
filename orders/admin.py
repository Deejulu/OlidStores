from django.contrib import admin
from .models import Order, OrderItem, Cart, CartItem, CheckoutSettings, PaymentSettings, PaymentTransaction, WebhookEvent

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'payment_method', 'status', 'created_at', 'receipt_link')
	list_filter = ('status', 'payment_method', 'created_at')
	search_fields = ('user__email', 'id')
	actions = ['approve_manual_payments']
	list_filter = ('status', 'created_at')
	search_fields = ('user__email', 'id')
	actions = ['approve_manual_payments']

	def approve_manual_payments(self, request, queryset):
		updated = queryset.filter(status='Pending', receipt__isnull=False).update(status='Processing')
		self.message_user(request, f"{updated} order(s) marked as Processing.")
	approve_manual_payments.short_description = "Approve selected manual payment orders (set to Processing)"

	def receipt_link(self, obj):
		if obj.receipt:
			return f'<a href="{obj.receipt.url}" target="_blank">View Receipt</a>'
		return '-'
	receipt_link.allow_tags = True
	receipt_link.short_description = 'Receipt'

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
	list_display = ('order', 'product', 'quantity', 'price')
	search_fields = ('order__id', 'product__name')

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
	list_display = ('user', 'created_at')
	search_fields = ('user__email',)

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
	list_display = ('cart', 'product', 'quantity')
	search_fields = ('cart__id', 'product__name')

@admin.register(CheckoutSettings)
class CheckoutSettingsAdmin(admin.ModelAdmin):
	list_display = ('delivery_fee_24h', 'delivery_fee_2d', 'updated_at')
	list_editable = ('delivery_fee_24h', 'delivery_fee_2d')
	readonly_fields = ('updated_at',)
	fieldsets = (
		("Delivery Fees", {
			'fields': ('delivery_fee_24h', 'delivery_fee_2d')
		}),
		("Metadata", {
			'fields': ('updated_at',),
		}),
	)
	list_display_links = None

@admin.register(PaymentSettings)
class PaymentSettingsAdmin(admin.ModelAdmin):
	list_display = ('enable_paystack', 'enable_manual_transfer', 'enable_pay_on_delivery', 'pay_on_delivery_max', 'updated_at')
	list_editable = ('enable_paystack', 'enable_manual_transfer', 'enable_pay_on_delivery', 'pay_on_delivery_max')
	readonly_fields = ('updated_at',)
	fieldsets = (
		("Payment Options", {
			'fields': ('enable_paystack', 'enable_manual_transfer', 'enable_pay_on_delivery', 'pay_on_delivery_max')
		}),
		("Metadata", {
			'fields': ('updated_at',),
		}),
	)
	list_display_links = None

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
	list_display = ('reference', 'order', 'payment_method', 'amount', 'currency', 'status', 'created_at')
	list_filter = ('status', 'currency', 'created_at')
	search_fields = ('reference', 'order__id', 'order__full_name')
	readonly_fields = ('created_at', 'raw_response')

@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
	list_display = ('provider', 'event_type', 'reference', 'processed', 'created_at')
	list_filter = ('provider', 'processed', 'created_at')
	search_fields = ('reference', 'event_type')
	readonly_fields = ('created_at', 'headers', 'payload', 'response_text')
