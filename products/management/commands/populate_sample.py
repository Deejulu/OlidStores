from django.core.management.base import BaseCommand
from products.models import Category, Product
import random
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Populate the database with sample categories and products.'

    def handle(self, *args, **options):
        categories = [
            'Electronics', 'Fashion', 'Home Appliances', 'Cosmetics', 'Books', 'Sports', 'Toys', 'Furniture', 'Gaming'
        ]
        created_cats = []
        for cat_name in categories:
            cat, created = Category.objects.get_or_create(name=cat_name)
            created_cats.append(cat)
        self.stdout.write(self.style.SUCCESS(f'Created {len(created_cats)} categories.'))

        sample_products = [
            ('Classic T-Shirt', 'A comfortable cotton t-shirt.'),
            ('Denim Jeans', 'Stylish blue jeans for everyday wear.'),
            ('Sneakers', 'Trendy sneakers for all occasions.'),
            ('Leather Belt', 'Premium quality leather belt.'),
            ('Summer Dress', 'Light and breezy dress for summer.'),
            ('Sports Watch', 'Water-resistant digital sports watch.'),
            ('Backpack', 'Spacious and durable backpack.'),
            ('Running Shoes', 'Lightweight running shoes for athletes.'),
            ('Kids Hoodie', 'Warm hoodie for kids.'),
            ('Sunglasses', 'UV-protected stylish sunglasses.'),
            ('Rechargeable Fan', 'Rechargeable fan with long-lasting battery.'),
            ('Solar Charger', 'Solar charger for eco-friendly phone charging.'),
            ('Gaming Keyboard', 'Mechanical keyboard with RGB lighting.'),
            ('Office Chair', 'Ergonomic office chair with lumbar support.'),
            ('Water Bottle', 'Insulated stainless steel water bottle.'),
            ('Blender', 'Multi-speed kitchen blender.'),
            ('Cookbook', 'Recipe book for healthy meals.'),
            ('Face Serum', 'Brightening vitamin C serum.'),
            ('Desk Lamp', 'Adjustable LED desk lamp.'),
            ('Board Game', 'Fun family board game for 2-6 players.'),
            ('Novel', 'Enjoyable bestselling novel.'),
            ('Bike Helmet', 'Durable safety helmet for cycling.'),
            ('Play Tent', 'Kids play tent with removable cover.'),
            ('Bluetooth Speaker', 'Portable Bluetooth speaker with rich bass.'),
            ('Laptop Stand', 'Adjustable laptop stand for desk use.'),
        ]

        # Remove any existing products first so the sample data is regenerated cleanly.
        Product.objects.all().delete()
        self.stdout.write(self.style.WARNING('Deleted existing products before populating sample inventory.'))

        target_count = 100
        for start_index in range(target_count):
            base_name, desc = sample_products[start_index % len(sample_products)]
            repeat_index = start_index // len(sample_products)
            if repeat_index == 0:
                name = base_name
            else:
                name = f"{base_name} #{repeat_index + 1}"

            # Assign Electronics products to the correct category
            if base_name in ['Rechargeable Fan', 'Powerpoint', 'Solar Charger']:
                category = Category.objects.get(name='Electronics')
            else:
                category = random.choice([cat for cat in created_cats if cat.name != 'Electronics'])

            price = round(random.uniform(10, 100), 2)
            stock = random.randint(5, 50)
            base_slug = slugify(name)
            slug = base_slug
            i = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{i}"
                i += 1
            Product.objects.create(
                name=name,
                description=desc,
                price=price,
                stock=stock,
                category=category,
                slug=slug
            )

        self.stdout.write(self.style.SUCCESS(f'Sample products created: {target_count}. Total products now: {Product.objects.count()}'))
