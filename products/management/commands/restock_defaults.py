from django.core.management.base import BaseCommand
from products.models import Product

class Command(BaseCommand):
    help = 'Restocks products with zero stock to sensible defaults (reorder_level*2 or 20).'

    def handle(self, *args, **options):
        products = Product.objects.filter(stock=0)
        count = 0
        for p in products:
            if getattr(p, 'reorder_level', None) and p.reorder_level > 0:
                p.stock = p.reorder_level * 2
            else:
                p.stock = 20
            p.save()
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Restocked {count} products.'))
