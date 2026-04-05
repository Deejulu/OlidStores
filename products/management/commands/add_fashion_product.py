from django.core.management.base import BaseCommand
from products.models import Category, Product
from django.core.files import File
import os

class Command(BaseCommand):
    help = 'Add another modern product with mobile-responsive features.'

    def handle(self, *args, **options):
        # Create categories if they don't exist
        fashion, created = Category.objects.get_or_create(
            name='Fashion',
            defaults={'description': 'Trendy fashion and clothing items'}
        )

        # Create the new product
        product, created = Product.objects.get_or_create(
            name='Premium Leather Crossbody Bag',
            defaults={
                'description': 'Elegant genuine leather crossbody bag with adjustable strap, multiple compartments, and timeless design. Perfect for everyday use or special occasions with RFID protection and water-resistant material.',
                'price': 149.99,
                'stock': 15,
                'category': fashion,
                'slug': 'premium-leather-crossbody-bag'
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created new product: {product.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'Product already exists: {product.name}'))

        self.stdout.write(self.style.SUCCESS('Product creation completed!'))