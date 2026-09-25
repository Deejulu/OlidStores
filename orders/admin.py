from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem, Cart, CartItem, CheckoutSettings, PaymentSettings, PaymentTransaction, WebhookEvent


def order_item_image(obj):
    """Return a small thumbnail for an OrderItem's product image."""
    product = getattr(obj, "product", None)
    image = getattr(product, "image", None) if product else None
    if image:
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">'
            '<img src="{}" alt="{}" style="width:48px;height:48px;'
            'object-fit:cover;border-radius:6px;"></a>',
            image.url, image.url, product.name,
        )
    name = getattr(product, "name", "") if product else ""
    initial = (name[:1] or "?").upper()
    return format_html(
        '<span style="display:inline-flex;align-items:center;justify-content:center;'
        'width:48px;height:48px;border-radius:6px;background:var(--bg-secondary);'
        'border:1px solid var(--border-color);font-weight:700;">{}</span>', initial
    )

class OrderItemInline(admin.TabularInline):
	model = OrderItem
	extra = 0
	can_delete = False
	fields = ('image_tag', 'product', 'variant', 'quantity', 'price', 'subtotal')
	readonly_fields = ('image_tag', 'product', 'variant', 'quantity', 'price', 'subtotal')

	def image_tag(self, obj):
		return order_item_image(obj)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'payment_method', 'status', 'created_at', 'receipt_link')
	list_filter = ('status', 'payment_method', 'created_at')
	search_fields = ('user__email', 'id')
	actions = ['approve_manual_payments']
	inlines = (OrderItemInline,)

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
	list_display = ('order', 'image_tag', 'product', 'quantity', 'price', 'subtotal')
	list_display_links = ('product',)
	search_fields = ('order__id', 'product__name')

	def image_tag(self, obj):
		return order_item_image(obj)
	image_tag.short_description = 'Image'

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
