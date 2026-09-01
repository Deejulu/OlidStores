"""One-off seed script for the Olid Stores chat demo (local SQLite sandbox only).

Creates a logged-in customer 'alice' with real orders and payment transactions
so the live chat widget can answer account-specific questions with real data.

Usage:
    python seed_chat_demo.py --settings=e_stores.settings_local_sqlite
"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_stores.settings_local_sqlite')

import django
django.setup()

from django.contrib.auth import get_user_model
from orders.models import Order, PaymentTransaction

U = get_user_model()
u, created = U.objects.get_or_create(
    username='alice',
    defaults={'first_name': 'Alice', 'last_name': 'Ade',
              'email': 'alice@example.com', 'is_active': True},
)
# Force-set the demo password on every run (idempotent) so the live transcript
# can always log in as alice / pass123. A prior seed run may have left a
# different usable password in place.
u.set_password('pass123')
u.is_active = True
u.save()

# Idempotency: clear alice's existing demo orders/payments. Delete payment
# transactions BEFORE orders (some Order->PaymentTransaction FKs are SET_NULL,
# which would orphan transactions on order delete), and also sweep any stale
# transactions by reference so the unique `reference` constraint never clashes.
from orders.models import PaymentTransaction
PaymentTransaction.objects.filter(order__user=u).delete()
PaymentTransaction.objects.filter(reference__in=['ref_alice_1', 'ref_alice_2']).delete()
Order.objects.filter(user=u).delete()

o1 = Order.objects.create(
    user=u, full_name='Alice Ade', phone='08010000001',
    email='alice@example.com', delivery_address='1 Alice Street, Lagos',
    total=15000, status='Shipped', tracking_number='TRK-ALICE-0001',
    payment_method='paystack',
)
o2 = Order.objects.create(
    user=u, full_name='Alice Ade', phone='08010000001',
    email='alice@example.com', delivery_address='1 Alice Street, Lagos',
    total=8000, status='Processing', tracking_number='TRK-ALICE-0002',
    payment_method='paystack',
)
PaymentTransaction.objects.create(
    order=o1, reference='ref_alice_1', amount=15000,
    currency='NGN', status='success', payment_method='card',
)
PaymentTransaction.objects.create(
    order=o2, reference='ref_alice_2', amount=8000,
    currency='NGN', status='pending', payment_method='card',
)

print("Seeded user: %s (%s) password=pass123" % (u.username, u.email))
print("Orders: %s (#%s, %s), %s (#%s, %s)"
      % (o1.number, o1.number, o1.status, o2.number, o2.number, o2.status))
