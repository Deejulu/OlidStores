"""
Check Order #36 data to see what's stored in database
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_stores.settings')
django.setup()

from orders.models import Order, PaymentTransaction

order = Order.objects.get(id=36)

print("=" * 70)
print("ORDER #36 DATABASE VALUES")
print("=" * 70)
print(f"order.total (products subtotal):  ₦{order.total:,.2f}")
print(f"order.delivery_fee:                ₦{order.delivery_fee:,.2f}")
print(f"order.grand_total() (calculated):  ₦{order.grand_total():,.2f}")
print()

# Check payment
payment = PaymentTransaction.objects.filter(order=order).first()
if payment:
    print("PAYSTACK PAYMENT:")
    print(f"Amount paid:       ₦{payment.amount:,.2f}")
    print(f"Reference:         {payment.reference}")
    print(f"Status:            {payment.status}")
    print()

print("=" * 70)
print("DIAGNOSIS:")
print("=" * 70)

expected_grand_total = order.total + order.delivery_fee
products_only = order.total - order.delivery_fee

if payment:
    if payment.amount == order.total:
        print(f"⚠️  PROBLEM: Customer paid ₦{payment.amount:,.2f}")
        print(f"   This equals order.total (₦{order.total:,.2f})")
        print(f"   Which INCLUDES delivery fee already!")
        print(f"   So grand_total() adds it AGAIN: ₦{order.total:,.2f} + ₦{order.delivery_fee:,.2f} = ₦{expected_grand_total:,.2f}")
        print()
        print("   ACTUAL products subtotal should be: ₦{:,.2f}".format(products_only))
        print("   Customer paid correctly: ₦{:,.2f}".format(payment.amount))
        print("   But database is storing wrong values!")
