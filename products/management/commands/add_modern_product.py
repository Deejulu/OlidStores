from django.core.management.base import BaseCommand
from products.models import Category, Product, ProductImage
from django.core.files import File
import os

class Command(BaseCommand):
    help = 'Add a new modern product with mobile-responsive features.'

    def handle(self, *args, **options):
        # Create Electronics category if it doesn't exist
        electronics, created = Category.objects.get_or_create(
            name='Electronics',
            defaults={'description': 'Modern electronic devices and gadgets'}
        )

        # Create the new product
        product, created = Product.objects.get_or_create(
            name='Wireless Bluetooth Earbuds Pro',
            defaults={
                'description': 'Premium wireless earbuds with active noise cancellation, 30-hour battery life, and touch controls. Perfect for calls, music, and workouts with superior sound quality.',
                'price': 89.99,
                'stock': 25,
                'category': electronics,
                'slug': 'wireless-bluetooth-earbuds-pro'
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created new product: {product.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'Product already exists: {product.name}'))

        # Note: In a real scenario, you would upload actual images here
        # For now, we'll just create the product without images
        self.stdout.write(self.style.SUCCESS('Product creation completed!'))