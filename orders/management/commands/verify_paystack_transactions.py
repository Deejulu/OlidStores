from django.core.management.base import BaseCommand
from orders.models import PaymentTransaction
from orders.utils import verify_paystack_reference

class Command(BaseCommand):
    help = 'Verify pending or failed Paystack PaymentTransaction records against Paystack API'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100, help='Max transactions to verify')

    def handle(self, *args, **options):
        limit = options.get('limit')
        qs = PaymentTransaction.objects.filter(status__in=['', 'failed', 'pending']).order_by('created_at')[:limit]
        count = 0
        for tx in qs:
            resp = verify_paystack_reference(tx.reference)
            if resp and resp.get('status'):
                data = resp.get('data', {})
                tx.status = data.get('status', tx.status)
                tx.raw_response = data
                tx.amount = float(data.get('amount', 0)) / 100.0
                tx.currency = data.get('currency', tx.currency)
                tx.save()
                count += 1
        self.stdout.write(self.style.SUCCESS(f'Verified {count} transaction(s)'))
