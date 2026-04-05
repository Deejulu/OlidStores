from products.models import Category, Product

categories = [
    ('Electronics', 'Gadgets and devices'),
    ('Fashion', 'Clothing and accessories'),
    ('Home Appliances', 'Kitchen and home devices'),
    ('Cosmetics', 'Beauty and skincare'),
    ('Books', 'Fiction and non-fiction books'),
    ('Sports', 'Fitness and outdoor equipment'),
    ('Toys', 'Children toys and games'),
    ('Furniture', 'Home and office furniture'),
    ('Gaming', 'Consoles, accessories and games'),
]

cat_objs = {}
for name, desc in categories:
    c, _ = Category.objects.get_or_create(name=name, defaults={'description': desc})
    cat_objs[name] = c

products = [
    ('Smartphone', 'Latest 5G smartphone', 699.99, 25, 'Electronics'),
    ('Wireless Earbuds', 'Noise-isolating wireless earbuds', 59.99, 35, 'Electronics'),
    ('Yoga Mat', 'Non-slip yoga mat for home workouts', 24.99, 60, 'Sports'),
    ('Sneakers', 'Lightweight running sneakers', 89.99, 40, 'Fashion'),
    ('Kitchen Mixer', 'Multi-speed stand mixer', 139.99, 18, 'Home Appliances'),
    ('Moisturizing Cream', 'Daily hydrating face cream', 21.99, 80, 'Cosmetics'),
    ('Denim Jacket', 'Classic denim jacket with button closure', 74.99, 45, 'Fashion'),
    ('Office Chair', 'Ergonomic swivel office chair', 149.99, 12, 'Furniture'),
    ('Children Puzzle', '100-piece educational puzzle', 14.99, 90, 'Toys'),
    ('Cookbook', 'Healthy recipes for all skill levels', 24.99, 32, 'Books'),
    ('Blender', 'High-speed kitchen blender', 89.99, 40, 'Home Appliances'),
    ('Gaming Keyboard', 'Mechanical keyboard with RGB lighting', 99.99, 22, 'Gaming'),
    ('Face Serum', 'Vitamin C brightening serum', 18.99, 75, 'Cosmetics'),
    ('Stylish Handbag', 'Leather-look tote bag', 49.99, 30, 'Fashion'),
    ('Portable Speaker', 'Waterproof Bluetooth speaker', 39.99, 50, 'Electronics'),
    ('Bookshelf', 'Three-tier leaning bookshelf', 99.99, 10, 'Furniture'),
    ('Soccer Ball', 'Standard size soccer ball', 19.99, 55, 'Sports'),
    ('Board Game', 'Family board game for 2-6 players', 29.99, 70, 'Toys'),
    ('Microwave', 'Compact microwave oven', 119.99, 20, 'Home Appliances'),
    ('Fantasy Novel', 'Epic fantasy adventure novel', 16.99, 60, 'Books'),
]

for name, desc, price, stock, cat_name in products:
    cat = cat_objs[cat_name]
    Product.objects.get_or_create(name=name, defaults={'description': desc, 'price': price, 'stock': stock, 'category': cat})

print('Sample categories and products created.')
