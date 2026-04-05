from products.models import Category, Product

categories = [
    ('Electronics', 'Gadgets and devices'),
    ('Fashion', 'Clothing and accessories'),
    ('Home Appliances', 'Kitchen and home devices'),
    ('Cosmetics', 'Beauty and skincare'),
    ('Books', 'Fiction and non-fiction books'),
]

cat_objs = {}
for name, desc in categories:
    c, _ = Category.objects.get_or_create(name=name, defaults={'description': desc})
    cat_objs[name] = c

products = [
    ('Smartphone', 'Latest 5G smartphone', 699.99, 25, 'Electronics'),
    ('Blender', 'High-speed kitchen blender', 89.99, 40, 'Home Appliances'),
    ('Lipstick', 'Matte finish lipstick', 14.99, 100, 'Cosmetics'),
    ('Jeans', 'Slim fit blue jeans', 49.99, 60, 'Fashion'),
    ('Cookbook', 'Healthy recipes for all', 24.99, 30, 'Books'),
    ('Headphones', 'Noise-cancelling headphones', 129.99, 15, 'Electronics'),
    ('Dress', 'Summer floral dress', 39.99, 50, 'Fashion'),
    ('Microwave', 'Compact microwave oven', 119.99, 20, 'Home Appliances'),
    ('Face Cream', 'Hydrating face cream', 19.99, 80, 'Cosmetics'),
    ('Novel', 'Bestselling mystery novel', 17.99, 45, 'Books'),
]

for name, desc, price, stock, cat_name in products:
    cat = cat_objs[cat_name]
    Product.objects.get_or_create(name=name, defaults={'description': desc, 'price': price, 'stock': stock, 'category': cat})

print('Sample categories and products created.')
