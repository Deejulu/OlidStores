import sys
import logging
import threading
import uuid
from django.db import connection, transaction
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta
import random
from django.utils.text import slugify as _slugify

logger = logging.getLogger(__name__)

RUNNING_TESTS = 'test' in sys.argv or 'pytest' in sys.argv
JOB_STATUS = {}
JOB_STATUS_LOCK = threading.Lock()


def update_job_status(job_id, *, status='running', message='Working...', percent=None, done=False, error=None):
    if not job_id:
        return
    payload = {
        'status': status,
        'message': message,
        'done': done,
        'error': error,
        'percent': percent if percent is not None else 0,
    }
    with JOB_STATUS_LOCK:
        current = JOB_STATUS.get(job_id, {})
        current.update(payload)
        JOB_STATUS[job_id] = current


def get_job_status(job_id):
    with JOB_STATUS_LOCK:
        data = JOB_STATUS.get(job_id, {})
        return {
            'job_id': job_id,
            'status': data.get('status', 'unknown'),
            'message': data.get('message', 'No status available.'),
            'percent': data.get('percent', 0),
            'done': bool(data.get('done', False)),
            'error': data.get('error'),
        }


def _run_in_thread(func, *args, **kwargs):
    if RUNNING_TESTS:
        func(*args, **kwargs)
        return None

    job_id = kwargs.pop('job_id', None) or str(uuid.uuid4())
    update_job_status(job_id, status='queued', message=f'{getattr(func, "__name__", "task")} queued.', percent=0, done=False)

    def wrapper():
        connection.close()
        try:
            update_job_status(job_id, status='running', message=f'{getattr(func, "__name__", "task")} started.', percent=5, done=False)
            func(*args, job_id=job_id, **kwargs)
            update_job_status(job_id, status='completed', message=f'{getattr(func, "__name__", "task")} completed.', percent=100, done=True)
        except Exception as e:
            logger.error(f'Background task failed: {e}', exc_info=True)
            update_job_status(job_id, status='failed', message=f'{getattr(func, "__name__", "task")} failed.', percent=100, done=True, error=str(e))

    t = threading.Thread(target=wrapper, daemon=True)
    t.start()
    return job_id


def do_product_populate_sample(job_id=None):
    try:
        update_job_status(job_id, status='running', message='Preparing product catalog...', percent=25)
        call_command('populate_sample')
        update_job_status(job_id, status='completed', message='Sample products were added successfully.', percent=100, done=True)
    except Exception as e:
        logger.error(f'Background product populate failed: {e}', exc_info=True)
        update_job_status(job_id, status='failed', message='Sample products failed to populate.', percent=100, done=True, error=str(e))
        raise


def do_populate_sample_data_full(job_id=None):
    User = get_user_model()
    from products.models import Category, Product
    from orders.models import Order, OrderItem, PaymentTransaction

    update_job_status(job_id, status='running', message='Preparing sample catalog...', percent=8)

    CATALOG = {
        'Electronics': [
            ('Wireless Earbuds', 'True wireless earbuds with active noise cancellation and 24-hour battery life.', 35, 150),
            ('Bluetooth Speaker', 'Portable waterproof speaker with 360° rich bass sound.', 45, 120),
            ('USB-C Hub', '7-in-1 USB-C hub with HDMI, SD card, and 3 USB-A ports.', 28, 80),
            ('Mechanical Keyboard', 'Compact tenkeyless keyboard with RGB backlight and tactile switches.', 75, 60),
            ('Webcam HD', '1080p webcam with built-in noise-cancelling microphone for video calls.', 55, 90),
            ('Laptop Stand', 'Adjustable aluminium laptop stand for ergonomic desk use.', 32, 100),
            ('Solar Charger', '20W foldable solar panel charger compatible with all USB devices.', 48, 70),
            ('Smart Plug', 'Wi-Fi enabled smart plug with energy monitoring and voice control.', 18, 150),
            ('Rechargeable Fan', 'Portable desk fan with 5000mAh rechargeable battery and 3 speeds.', 25, 110),
            ('LED Desk Lamp', 'Touch-controlled LED lamp with 5 colour temperatures and USB charging port.', 38, 95),
            ('Portable Power Bank', '20000mAh power bank with dual USB-C fast charging output.', 42, 130),
            ('Wireless Mouse', 'Ergonomic silent wireless mouse with 2.4GHz nano receiver.', 22, 140),
            ('Smart Watch', 'Fitness smartwatch with heart rate monitor, GPS, and 7-day battery.', 89, 75),
            ('Action Camera', '4K action camera with waterproof case, wide-angle lens, and image stabilisation.', 65, 70),
            ('Portable Projector', 'Mini LED projector with 200-lumen output, HDMI and USB inputs.', 95, 55),
        ],
        'Fashion': [
            ('Classic White T-Shirt', 'Premium 100% cotton crew-neck tee, perfect for everyday wear.', 12, 200),
            ('Slim-Fit Denim Jeans', 'Modern slim-fit jeans crafted from stretch denim for all-day comfort.', 38, 150),
            ('Leather Sneakers', 'Minimalist leather sneakers with cushioned insole and rubber sole.', 65, 100),
            ('Canvas Backpack', 'Durable canvas backpack with laptop sleeve and multiple pockets.', 45, 120),
            ('Sunglasses UV400', 'Polarised sunglasses with full UV400 protection and lightweight frame.', 28, 180),
            ('Summer Floral Dress', 'Lightweight floral wrap dress, ideal for warm weather occasions.', 35, 130),
            ('Leather Belt', 'Genuine leather reversible belt available in black and brown.', 22, 160),
            ('Knit Beanie', 'Soft ribbed-knit beanie hat, one size fits all.', 14, 200),
            ('Chinos Trouser', 'Smart casual stretch chinos available in multiple colours.', 42, 140),
            ('Puffer Jacket', 'Lightweight water-resistant puffer jacket with packable design.', 78, 90),
            ('Polo Shirt', 'Classic polo shirt made from breathable piqué cotton.', 24, 170),
            ('Ankle Boots', 'Chelsea-style ankle boots with elastic side panels and block heel.', 72, 85),
            ('Hoodie Sweatshirt', 'Fleece-lined pullover hoodie with kangaroo pocket.', 34, 160),
            ('Crossbody Bag', 'Compact vegan leather crossbody bag with adjustable strap.', 39, 110),
        ],
        'Home Appliances': [
            ('Air Fryer', '4-litre digital air fryer with 8 preset cooking modes and timer.', 85, 70),
            ('Electric Kettle', '1.7L stainless steel cordless kettle with rapid-boil technology.', 32, 110),
            ('Stand Blender', '1000W high-speed blender with 6-blade assembly and 1.5L jug.', 58, 80),
            ('Rice Cooker', '1.8L digital rice cooker with steamer basket and keep-warm function.', 44, 95),
            ('Microwave Oven', '20L solo microwave with 5 power levels and defrost setting.', 95, 55),
            ('Sandwich Toaster', 'Non-stick sandwich maker with cool-touch handle and indicator light.', 26, 120),
            ('Handheld Vacuum', 'Cordless handheld vacuum with HEPA filter and 20-minute runtime.', 48, 85),
            ('Iron Box', '2200W steam iron with self-cleaning function and anti-drip system.', 36, 100),
            ('Electric Kettle Mini', '0.5L travel-size kettle with dual voltage support (110V/220V).', 22, 130),
            ('Dish Drying Rack', 'Stainless steel two-tier dish drying rack with drip tray.', 28, 140),
            ('Ceiling Fan Remote', 'Universal ceiling fan remote control kit with timer function.', 18, 160),
            ('Water Purifier Jug', '3.5L pitcher with activated carbon filter, removes 99% of chlorine.', 35, 110),
            ('Electric Can Opener', 'Cordless automatic electric can opener, safe edge technology.', 20, 120),
        ],
        'Cosmetics': [
            ('Vitamin C Serum', 'Brightening 20% vitamin C face serum with hyaluronic acid.', 24, 150),
            ('Moisturising Sunscreen SPF50', 'Lightweight SPF50 daily sunscreen with moisturising formula.', 18, 180),
            ('Matte Lipstick', 'Long-wear matte lipstick in 12 rich shades, hydrating formula.', 12, 200),
            ('Face Wash Gel', 'Gentle foaming gel cleanser for oily and combination skin.', 14, 190),
            ('Eyeshadow Palette', '18-shade neutral eyeshadow palette with matte and shimmer finishes.', 28, 140),
            ('Hair Growth Oil', 'Castor and argan oil blend for scalp treatment and hair growth.', 20, 165),
            ('Collagen Face Mask', 'Pack of 5 hydrogel collagen sheet masks for intensive hydration.', 16, 210),
            ('BB Cream', 'Tinted moisturiser with SPF30 and buildable medium coverage.', 22, 170),
            ('Nail Polish Set', 'Set of 10 chip-resistant nail polishes in trending seasonal colours.', 18, 155),
            ('Under Eye Patches', '60-piece gold collagen under-eye patches to reduce puffiness.', 15, 180),
            ('Setting Spray', 'Long-lasting makeup setting spray for up to 16-hour wear.', 17, 160),
            ('Beard Balm', 'Natural conditioning beard balm with shea butter and cedarwood oil.', 14, 130),
            ('Body Scrub', 'Coffee and coconut exfoliating body scrub for smooth, glowing skin.', 16, 145),
        ],
        'Books': [
            ('Atomic Habits', "James Clear's guide to building good habits and breaking bad ones.", 14, 100),
            ('Rich Dad Poor Dad', "Robert Kiyosaki's personal finance classic on building wealth.", 12, 120),
            ('The Alchemist', "Paulo Coelho's beloved novel about following your personal legend.", 11, 130),
            ('Think and Grow Rich', "Napoleon Hill's timeless principles of success and achievement.", 11, 115),
            ('Ikigai', 'Japanese concept guide to finding purpose and living a longer life.', 13, 110),
            ('The 48 Laws of Power', "Robert Greene's definitive guide to power, strategy and influence.", 15, 95),
            ('Sapiens', "Yuval Noah Harari's sweeping history of humankind.", 16, 90),
            ('Mindset', "Carol Dweck's research on the power of believing you can improve.", 13, 105),
            ('Deep Work', "Cal Newport's rules for focused success in a distracted world.", 14, 100),
            ('The Psychology of Money', "Morgan Housel's timeless lessons on wealth, greed, and happiness.", 13, 110),
            ("Can't Hurt Me", "David Goggins' memoir about overcoming adversity and self-discipline.", 15, 95),
            ('Start With Why', "Simon Sinek's exploration of what makes great leaders inspire action.", 13, 105),
            ('Zero to One', "Peter Thiel's notes on startups and building the future.", 14, 90),
        ],
        'Sports': [
            ('Yoga Mat', 'Non-slip 6mm thick TPE yoga mat with carry strap and alignment lines.', 28, 110),
            ('Resistance Bands Set', 'Set of 5 latex resistance bands ranging from 5lb to 50lb.', 22, 130),
            ('Jump Rope Speed', 'Ball-bearing speed jump rope with adjustable cable and foam handles.', 14, 160),
            ('Gym Gloves', 'Padded weightlifting gloves with wrist support and anti-slip grip.', 18, 150),
            ('Running Shoes', 'Lightweight mesh running shoes with responsive foam sole.', 58, 90),
            ('Cycling Helmet', 'Aerodynamic road cycling helmet with 18 ventilation channels.', 45, 75),
            ('Football', 'FIFA-quality match football, size 5, durable PU leather casing.', 28, 120),
            ('Swimming Goggles', 'Anti-fog UV-protected swimming goggles with adjustable strap.', 16, 140),
            ('Dumbbell Pair 5kg', 'Pair of rubber hex dumbbells, 5kg each, non-roll design.', 35, 100),
            ('Sports Bottle 1L', 'BPA-free 1-litre sports water bottle with flip-cap and carry loop.', 12, 200),
            ('Foam Roller', '33cm high-density EVA foam roller for muscle recovery and massage.', 20, 135),
            ('Tennis Racket', 'Aluminium frame beginner tennis racket with grip tape included.', 38, 80),
            ('Skipping Board', 'Wooden balance board for core training and coordination exercises.', 32, 90),
        ],
        'Toys': [
            ('LEGO Classic Brick Set', '500-piece classic LEGO brick set for creative free-building play.', 38, 85),
            ('Remote Control Car', 'High-speed 1:16 scale RC car with 2.4GHz control and 30-min battery.', 45, 75),
            ('Kids Art Set', '120-piece art and craft kit including crayons, paints, and brushes.', 22, 100),
            ('Stuffed Teddy Bear', 'Soft plush teddy bear, 45cm, hypoallergenic filling, machine washable.', 16, 150),
            ('Wooden Puzzle 100pc', '100-piece jigsaw puzzle with vibrant wildlife illustration for ages 5+.', 14, 120),
            ('Play Kitchen Set', 'Realistic pretend-play kitchen set with 25 accessories included.', 55, 60),
            ('Magnetic Drawing Board', 'Mess-free magnetic drawing and writing tablet for ages 3+.', 18, 130),
            ('Bubble Machine', 'Automatic electric bubble machine producing 500+ bubbles per minute.', 24, 110),
            ('Building Blocks 60pc', 'Soft foam building blocks in 6 shapes and 8 colours for toddlers.', 20, 125),
            ('Kids Walkie Talkies', 'Pair of durable walkie talkies with 3km range and torch function.', 28, 90),
            ('Play-Doh Modelling Set', '10-can modelling compound set with tools and activity cards.', 18, 140),
            ('Toy Doctor Kit', '20-piece toy doctor playset with stethoscope and carry case.', 22, 100),
            ('Dinosaur Figure Set', 'Set of 12 realistically painted dinosaur figurines, ages 3+.', 26, 105),
        ],
        'Furniture': [
            ('Ergonomic Office Chair', 'Adjustable lumbar support office chair with breathable mesh back.', 120, 40),
            ('Folding Study Desk', 'Space-saving folding desk with cable management and storage shelf.', 95, 50),
            ('Bedside Table', 'Minimalist bedside table with drawer and open shelf, easy assembly.', 65, 60),
            ('Bookshelf 5-Tier', 'Freestanding 5-tier open bookshelf in rustic brown finish.', 85, 45),
            ('TV Console Unit', 'Modern floating TV unit with two drawers for cable organisation.', 110, 35),
            ('Dining Chair Set x2', 'Set of 2 padded dining chairs in linen fabric with wooden legs.', 88, 50),
            ('Plastic Storage Cabinet', '4-drawer plastic storage cabinet for office or bedroom use.', 48, 75),
            ('Wardrobe 2-Door', 'Sliding 2-door wardrobe with hanging rail and 2 shelves.', 145, 30),
            ('Coffee Table', 'Round glass-top coffee table with chrome base, 90cm diameter.', 98, 40),
            ('Wall Floating Shelf', 'Set of 3 floating wall shelves in oak veneer finish.', 32, 95),
            ('Shoe Rack 4-Tier', 'Metal 4-tier shoe rack holding up to 20 pairs, rust-resistant.', 28, 110),
            ('Bean Bag Chair', 'Extra-large indoor bean bag with EPS filling and waterproof cover.', 55, 65),
            ('Standing Desk Converter', 'Height-adjustable desk converter, converts any desk to standing.', 78, 45),
        ],
        'Gaming': [
            ('Gaming Headset', '7.1 surround sound gaming headset with noise-cancelling microphone.', 55, 80),
            ('Gaming Controller', 'Wired USB gamepad compatible with PC, PS3, and Android devices.', 32, 100),
            ('Gaming Mouse Pad XL', 'Extended 90×40cm mouse pad with non-slip rubber base.', 18, 150),
            ('Gaming Chair', 'Racing-style gaming chair with lumbar pillow and reclining backrest.', 130, 35),
            ('Capture Card', 'USB 3.0 game capture card for HD 1080p60 streaming and recording.', 48, 70),
            ('PC Gaming Fan', '120mm ARGB case fan with PWM control and daisy-chain connector.', 14, 120),
            ('LED Strip Lights', '5-metre smart RGB LED strip with app control and music sync mode.', 22, 140),
            ('Gaming Desk', 'Carbon fibre-texture gaming desk with cup holder and monitor stand.', 115, 40),
            ('Steering Wheel', 'USB racing steering wheel with foot pedals for PC and consoles.', 72, 55),
            ('VR Headset', 'Standalone VR headset with 6DoF tracking and built-in speakers.', 95, 45),
            ('Mechanical Gaming Keyboard', 'Full-size mechanical keyboard with RGB per-key lighting and blue switches.', 68, 70),
            ('Gaming Router', 'Wi-Fi 6 gaming router with QoS, low latency, and MU-MIMO support.', 89, 50),
            ('Memory Card 256GB', 'High-speed 256GB microSDXC UHS-I card for game storage and transfers.', 28, 130),
        ],
    }

    try:
        with transaction.atomic():
            cat_names = list(CATALOG.keys())
            existing_cats = set(Category.objects.filter(name__in=cat_names).values_list('name', flat=True))
            new_cats = [Category(name=n, slug=_slugify(n), is_sample=True) for n in cat_names if n not in existing_cats]
            if new_cats:
                Category.objects.bulk_create(new_cats, ignore_conflicts=True)
            Category.objects.filter(name__in=cat_names, is_sample=False).update(is_sample=True)

            cat_objects = {c.name: c for c in Category.objects.filter(name__in=cat_names)}
            Product.objects.filter(is_sample=True).delete()

            to_create = []
            seen_slugs = set()
            for cat_name, products in CATALOG.items():
                category = cat_objects[cat_name]
                for name, description, base_price, base_stock in products:
                    price = round(base_price * random.uniform(0.9, 1.1), 2)
                    stock = random.randint(max(1, base_stock - 20), base_stock + 20)
                    base_slug = _slugify(name)
                    slug = base_slug
                    i = 1
                    while slug in seen_slugs:
                        slug = f'{base_slug}-{i}'
                        i += 1
                    seen_slugs.add(slug)
                    to_create.append(Product(
                        name=name, description=description, price=price,
                        stock=stock, category=category, slug=slug, is_sample=True,
                    ))
            Product.objects.bulk_create(to_create)

            cat_count = Category.objects.filter(is_sample=True).count()
            prod_count = Product.objects.filter(is_sample=True).count()

            sample_customers = []
            customer_names = [
                ('Adaobi Nwosu', 'adaobi.sample@example.com'),
                ('Chukwuemeka Okafor', 'emeka.sample@example.com'),
                ('Fatima Bello', 'fatima.sample@example.com'),
                ('Tunde Bakare', 'tunde.sample@example.com'),
                ('Ngozi Eze', 'ngozi.sample@example.com'),
                ('Ibrahim Musa', 'ibrahim.sample@example.com'),
                ('Funke Adeyemi', 'funke.sample@example.com'),
                ('Chioma Okonkwo', 'chioma.sample@example.com'),
                ('Emeka Ibrahim', 'emeka.i.sample@example.com'),
                ('Aisha Mohammed', 'aisha.sample@example.com'),
                ('Oluwaseun Adebayo', 'seun.sample@example.com'),
                ('Amina Yusuf', 'amina.sample@example.com'),
                ('Chinedu Eze', 'chinedu.sample@example.com'),
                ('Halima Abubakar', 'halima.sample@example.com'),
                ('Yemi Oladipo', 'yemi.sample@example.com'),
            ]

            existing_usernames = set(User.objects.filter(
                username__in=[email.split('@')[0] for _, email in customer_names]
            ).values_list('username', flat=True))

            new_customers = []
            for name, email in customer_names:
                username = email.split('@')[0]
                first_name = name.split()[0]
                if username not in existing_usernames:
                    new_customers.append(User(
                        username=username,
                        email=email,
                        first_name=first_name,
                        role='customer',
                        is_sample=True,
                        password=make_password('samplepass123'),
                    ))
                sample_customers.append(username)

            if new_customers:
                User.objects.bulk_create(new_customers)

            User.objects.filter(username__in=sample_customers, is_sample=False).update(is_sample=True)
            sample_customers_qs = User.objects.filter(username__in=sample_customers, role='customer')
            customer_count = sample_customers_qs.count()

            products = list(Product.objects.filter(is_sample=True))
            if not products:
                products = list(Product.objects.all()[:10])

            statuses = ['Completed', 'Completed', 'Completed', 'Completed', 'Processing', 'Shipped', 'Delivered', 'Cancelled']
            payment_methods = ['paystack', 'paystack', 'pay_on_delivery', 'manual']

            order_count = 0
            payment_count = 0
            item_count = 0

            orders_to_create = []
            order_items_to_create = []
            payments_to_create = []

            from django.utils import timezone as _tz
            year = _tz.now().year
            prefix = f"EST-{year}-"
            last_order = Order.objects.filter(number__startswith=prefix).order_by('-number').first()
            if last_order and last_order.number:
                try:
                    seq = int(last_order.number.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    seq = 1
            else:
                seq = 1

            for user in sample_customers_qs:
                existing_sample_orders = Order.objects.filter(user=user, is_sample=True).count()
                if existing_sample_orders > 0:
                    order_count += existing_sample_orders
                    item_count += OrderItem.objects.filter(order__user=user, is_sample=True).count()
                    payment_count += PaymentTransaction.objects.filter(order__user=user, is_sample=True).count()
                    continue

                num_orders = random.randint(4, 12)
                for _ in range(num_orders):
                    if random.random() < 0.6:
                        days_ago = random.randint(0, 30)
                    else:
                        days_ago = random.randint(31, 180)
                    created_at = timezone.now() - timedelta(days=days_ago, hours=random.randint(0, 23))
                    status = random.choice(statuses)
                    payment_method = random.choice(payment_methods)

                    order = Order(
                        user=user,
                        full_name=user.get_full_name() or user.username,
                        phone=f'080{random.randint(10000000, 99999999)}',
                        email=user.email,
                        delivery_address=f'{random.randint(1, 99)} Sample Street, Lagos',
                        delivery_fee=random.choice([0, 1500, 2000, 2500]),
                        total=0,
                        status=status,
                        payment_method=payment_method,
                        is_sample=True,
                        created_at=created_at,
                        updated_at=created_at,
                        number=f"{prefix}{seq:04d}",
                    )
                    orders_to_create.append(order)
                    seq += 1
                    order_count += 1

            Order.objects.bulk_create(orders_to_create)

            for order in orders_to_create:
                num_items = random.randint(1, 5)
                order_total = 0
                for _ in range(num_items):
                    product = random.choice(products)
                    qty = random.randint(1, 3)
                    price = product.price
                    order_items_to_create.append(OrderItem(
                        order=order,
                        product=product,
                        quantity=qty,
                        price=price,
                        is_sample=True,
                    ))
                    order_total += float(price) * qty
                    item_count += 1

                order.total = round(order_total, 2)

                if order.payment_method == 'paystack' or random.random() < 0.7:
                    payments_to_create.append(PaymentTransaction(
                        reference=f'SMP-{timezone.now().strftime("%Y%m%d")}-{order.id}-{random.randint(100000, 999999)}',
                        order=order,
                        amount=order.total + order.delivery_fee,
                        currency='NGN',
                        status='success' if order.status != 'Cancelled' else 'failed',
                        payment_method=order.payment_method,
                        raw_response={'sample': True},
                        is_sample=True,
                    ))
                    payment_count += 1

            OrderItem.objects.bulk_create(order_items_to_create)
            PaymentTransaction.objects.bulk_create(payments_to_create)

            Order.objects.bulk_update(orders_to_create, ['total'])

            return {
                'categories': cat_count,
                'products': prod_count,
                'customers': customer_count,
                'orders': order_count,
                'order_items': item_count,
                'payments': payment_count,
            }

    except Exception as e:
        logger.error(f'Background populate_sample_data_full failed: {e}', exc_info=True)
        raise
