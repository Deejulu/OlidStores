from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

# Import the checkout view directly so /checkout/ serves the checkout page
from orders.views import checkout_view

urlpatterns = [
	path('admin/', admin.site.urls),
	path('', include(('core.urls', 'core'), namespace='core')),
	path('shop/', include(('products.urls', 'products'), namespace='products')),
	path('cart/', include(('orders.urls', 'orders'), namespace='orders')),
	# Search is a top-level URL used by the header search form
	path('search/', include(('products.urls_search', 'products'), namespace='products_search')),
	# Provide a direct checkout route (kept for backward compatibility) and also keep the cart checkout under /cart/checkout/
	path('checkout/', checkout_view, name='checkout'),
	path('accounts/', include('users.urls')),
	path('admin-dashboard/', include('admin_dashboard.urls', namespace='admin_dashboard')),
]

if settings.DEBUG:
	urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
