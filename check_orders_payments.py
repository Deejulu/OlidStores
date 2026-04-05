"""
Quick check of current payment transactions and orders
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_stores.settings')
django.setup()

from orders.models import PaymentTransaction, Order

print("=" * 70)
print("CURRENT PAYMENT & ORDER STATUS")
print("=" * 70)

# Payment transactions
transactions = PaymentTransaction.objects.all().order_by('-created_at')
print(f"\n💳 All Payment Transactions ({transactions.count()}):")
print("-" * 70)

for tx in transactions:
    print(f"\nReference: {tx.reference}")
    print(f"  Status: {tx.status}")
    print(f"  Amount: ₦{tx.amount}")
    print(f"  Method: {tx.payment_method or 'N/A'}")
    print(f"  Created: {tx.created_at}")
    print(f"  Order: #{tx.order.id if tx.order else 'NOT LINKED'}")
    if tx.order:
        print(f"  Order Status: {tx.order.status}")
        print(f"  Order Total: ₦{tx.order.total}")
        print(f"  Order Customer: {tx.order.full_name}")

# Orders
print(f"\n\n📦 All Orders ({Order.objects.count()}):")
print("-" * 70)

orders = Order.objects.all().order_by('-created_at')
for order in orders:
    payment = order.paymenttransaction_set.first()
    print(f"\nOrder #{order.id}")
    print(f"  Status: {order.status}")
    print(f"  Total: ₦{order.total}")
    print(f"  Customer: {order.full_name}")
    print(f"  Created: {order.created_at}")
    print(f"  Payment: {payment.reference if payment else 'NO PAYMENT LINKED'}")
    if payment:
        print(f"  Payment Status: {payment.status}")

print("\n" + "=" * 70)
