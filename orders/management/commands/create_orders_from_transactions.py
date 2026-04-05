from django.core.management.base import BaseCommand
from orders.models import PaymentTransaction, Order, OrderItem

class Command(BaseCommand):
    help = 'Create Orders from unmatched PaymentTransaction records (for admin reconciliation)'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100, help='Max transactions to process')

    def handle(self, *args, **options):
        limit = options.get('limit')
        qs = PaymentTransaction.objects.filter(order__isnull=True).order_by('created_at')[:limit]
        created = 0
        for tx in qs:
            customer = tx.raw_response.get('customer') if isinstance(tx.raw_response, dict) else None
            email = customer.get('email') if customer else ''
            order = Order.objects.create(
                full_name=customer.get('first_name', 'Paystack Customer') if customer else 'Paystack Customer',
                phone='',
                email=email,
                delivery_address='From Paystack transaction',
                total=tx.amount or 0.0,
                status='Processing',
                notes='Created from Paystack transaction via management command'
            )
            OrderItem.objects.create(order=order, product=None, variant=None, quantity=1, price=tx.amount or 0.0)
            tx.order = order
            tx.save()
            created += 1
        self.stdout.write(self.style.SUCCESS(f'Created {created} order(s) from transactions'))
