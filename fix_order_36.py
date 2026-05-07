"""
Fix Order #36 - correct the total to be products only
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_stores.settings')
django.setup()

from orders.models import Order
from decimal import Decimal

order = Order.objects.get(id=36)

print("BEFORE FIX:")
print(f"order.total:        ₦{order.total:,.2f}")
print(f"order.delivery_fee: ₦{order.delivery_fee:,.2f}")
print(f"grand_total():      ₦{order.grand_total():,.2f}")
print()

# Calculate actual products subtotal from order items
products_subtotal = sum(item.subtotal() for item in order.items.all())

print(f"Calculated products subtotal from items: ₦{products_subtotal:,.2f}")
print()

# Update order.total to be products only
order.total = products_subtotal
order.save()

print("AFTER FIX:")
print(f"order.total:        ₦{order.total:,.2f}")
print(f"order.delivery_fee: ₦{order.delivery_fee:,.2f}")
print(f"grand_total():      ₦{order.grand_total():,.2f}")
print()
print("✅ Order #36 fixed!")
