from django.core.management.base import BaseCommand
from products.models import Category, Product

class Command(BaseCommand):
    help = 'Add a new accessory product to the catalog.'

    def handle(self, *args, **options):
        accessories, _ = Category.objects.get_or_create(
            name='Accessories',
            defaults={'description': 'Everyday accessories and small goods.'}
        )

        product, created = Product.objects.get_or_create(
            name='Sleek Wireless Charger Stand',
            defaults={
                'description': 'Fast wireless charger stand with adjustable angle and anti-slip base. Compatible with Qi-enabled devices.',
                'price': 39.99,
                'stock': 40,
                'category': accessories,
                'slug': 'sleek-wireless-charger-stand'
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created new product: {product.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'Product already exists: {product.name}'))
