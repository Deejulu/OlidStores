from django.core.management.base import BaseCommand
from django.utils import timezone
from orders.models import WebhookEvent
from orders.utils import process_paystack_webhook

class Command(BaseCommand):
    help = 'Process queued WebhookEvent records (retries with backoff)'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100)

    def handle(self, *args, **options):
        limit = options.get('limit')
        qs = WebhookEvent.objects.filter(processed=False).order_by('created_at')[:limit]
        processed = 0
        for ev in qs:
            ev.attempts += 1
            ev.last_attempt = timezone.now()
            try:
                ok, msg = process_paystack_webhook(ev.payload)
                ev.response_text = msg or ''
                if ok:
                    ev.processed = True
                    ev.processed_at = timezone.now()
                ev.save()
                processed += 1
            except Exception as e:
                ev.response_text = str(e)
                ev.save()
        self.stdout.write(self.style.SUCCESS(f'Processed {processed} webhook event(s)'))
