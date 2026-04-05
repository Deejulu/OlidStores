from django.core.management.base import BaseCommand
import random
from products.models import Product, ProductVariant

class Command(BaseCommand):
    help = 'Randomize stock across products and variants, ensuring no product has zero stock.'

    def add_arguments(self, parser):
        parser.add_argument('--min', type=int, default=5, help='Minimum stock value (inclusive)')
        parser.add_argument('--max', type=int, default=100, help='Maximum stock value (inclusive)')
        parser.add_argument('--seed', type=int, default=None, help='Optional random seed for reproducibility')
        parser.add_argument('--variants', action='store_true', help='Randomize variant stocks as well')
        parser.add_argument('--set-product-to-variants', action='store_true', help='If product has variants, set product.stock to the sum of its variants')

    def handle(self, *args, **options):
        min_val = max(1, options['min'])
        max_val = max(min_val, options['max'])
        seed = options['seed']
        randomize_variants = options['variants']
        sync_product_to_variants = options['set_product_to_variants']

        if seed is not None:
            random.seed(seed)

        products = Product.objects.all()
        prod_count = 0
        var_count = 0

        for p in products:
            prod_count += 1
            if randomize_variants and p.variants.exists():
                total = 0
                for v in p.variants.all():
                    v.stock = random.randint(min_val, max_val)
                    v.save(update_fields=['stock'])
                    var_count += 1
                    total += v.stock
                if sync_product_to_variants:
                    p.stock = total
                    p.save(update_fields=['stock'])
            else:
                # assign product-level stock
                p.stock = random.randint(min_val, max_val)
                p.save(update_fields=['stock'])

        self.stdout.write(self.style.SUCCESS(f'Randomized stock for {prod_count} products.'))
        if randomize_variants:
            self.stdout.write(self.style.SUCCESS(f'Randomized stock for {var_count} variants.'))
        self.stdout.write(self.style.SUCCESS('All updated stocks are at least 1 (no zeros).'))
