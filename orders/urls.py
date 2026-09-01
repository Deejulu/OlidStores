from django.urls import path
from .views import test_orders, cart_view, add_to_cart, checkout_view, cart_update_view, paystack_webhook, bulk_add_to_cart, order_history_view, order_detail_view, validate_cart_items, order_confirmation_view, download_order_pdf

urlpatterns = [
	# Primary cart/checkout endpoints (include is mounted at /cart/ in project urls)
	path('', cart_view, name='cart'),
	# Keep a small test route under /cart/test/ for diagnostics
	path('test/', test_orders, name='test'),
	path('add/', add_to_cart, name='add_to_cart'),
	path('bulk_add/', bulk_add_to_cart, name='bulk_add_to_cart'),
	path('checkout/', checkout_view, name='checkout'),
    path('update/', cart_update_view, name='cart_update'),
	path('validate/', validate_cart_items, name='validate_cart'),
	path('paystack/webhook/', paystack_webhook, name='paystack_webhook'),
    path('history/', order_history_view, name='order_history'),
    path('order/<int:order_id>/', order_detail_view, name='order_detail'),
    path('confirmation/<int:order_id>/<uuid:token>/', order_confirmation_view, name='order_confirmation'),
    path('confirmation/<int:order_id>/<uuid:token>/pdf/', download_order_pdf, name='order_confirmation_pdf'),
]
