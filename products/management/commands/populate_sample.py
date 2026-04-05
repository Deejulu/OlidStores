from django.core.management.base import BaseCommand
from products.models import Category, Product
import random
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Populate the database with sample categories and products.'

    def handle(self, *args, **options):
        categories = [
            'Men', 'Women', 'Kids', 'Accessories', 'Shoes', 'Bags', 'Watches', 'Sportswear', 'Electronics'
        ]
        # Remove any old 'Honda Electronics' category if it exists
        Category.objects.filter(name='Honda Electronics').delete()
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
            # Electronics products
            ('Rechargeable Fan', 'Electronics rechargeable fan with long-lasting battery.'),
            ('Powerpoint', 'Electronics Powerpoint for reliable power distribution.'),
            ('Solar Charger', 'Electronics solar charger for eco-friendly charging.'),
        ]
        for name, desc in sample_products:
            # Assign Electronics products to the correct category
            if name in ['Rechargeable Fan', 'Powerpoint', 'Solar Charger']:
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
        self.stdout.write(self.style.SUCCESS('Sample products created.'))
