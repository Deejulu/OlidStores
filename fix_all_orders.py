"""
Fix ALL orders that have the delivery fee double-counting bug
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_stores.settings')
django.setup()

from orders.models import Order
from decimal import Decimal

# Get all orders with delivery fee
orders = Order.objects.filter(delivery_fee__gt=0).order_by('id')

print("=" * 70)
print(f"Checking {orders.count()} orders with delivery fees...")
print("=" * 70)
print()

fixed_count = 0

for order in orders:
    # Calculate actual products subtotal from order items
    products_subtotal = sum(item.subtotal() for item in order.items.all())
    
    # Check if order.total includes delivery fee (buggy data)
    expected_total_with_delivery = products_subtotal + order.delivery_fee
    
    # If order.total is close to products + delivery, it's buggy
    if abs(order.total - expected_total_with_delivery) < Decimal('0.01'):
        print(f"Order #{order.id}:")
        print(f"  BEFORE: total=₦{order.total:,.2f}, delivery=₦{order.delivery_fee:,.2f}, grand_total=₦{order.grand_total():,.2f}")
        
        # Fix it
        order.total = products_subtotal
        order.save()
        
        print(f"  AFTER:  total=₦{order.total:,.2f}, delivery=₦{order.delivery_fee:,.2f}, grand_total=₦{order.grand_total():,.2f}")
        print(f"  ✅ Fixed!")
        print()
        fixed_count += 1

print("=" * 70)
print(f"✅ Fixed {fixed_count} orders")
print("=" * 70)
