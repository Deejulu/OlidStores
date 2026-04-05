from django.contrib import admin
from .models import Order, OrderItem, Cart, CartItem, CheckoutSettings

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'status', 'created_at', 'receipt_link')
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
