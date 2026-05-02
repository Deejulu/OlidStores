from django.core.management.base import BaseCommand
from products.models import Category, Product
import random
from django.utils.text import slugify


class Command(BaseCommand):
    help = 'Populate the database with 120 sample products across all categories.'

    # Exactly 120 products: 13-14 per category across 9 categories
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
            ('Atomic Habits', 'James Clear\'s guide to building good habits and breaking bad ones.', 14, 100),
            ('Rich Dad Poor Dad', 'Robert Kiyosaki\'s personal finance classic on building wealth.', 12, 120),
            ('The Alchemist', 'Paulo Coelho\'s beloved novel about following your personal legend.', 11, 130),
            ('Think and Grow Rich', 'Napoleon Hill\'s timeless principles of success and achievement.', 11, 115),
            ('Ikigai', 'Japanese concept guide to finding purpose and living a longer life.', 13, 110),
            ('The 48 Laws of Power', 'Robert Greene\'s definitive guide to power, strategy and influence.', 15, 95),
            ('Sapiens', 'Yuval Noah Harari\'s sweeping history of humankind.', 16, 90),
            ('Mindset', 'Carol Dweck\'s research on the power of believing you can improve.', 13, 105),
            ('Deep Work', 'Cal Newport\'s rules for focused success in a distracted world.', 14, 100),
            ('The Psychology of Money', 'Morgan Housel\'s timeless lessons on wealth, greed, and happiness.', 13, 110),
            ('Can\'t Hurt Me', 'David Goggins\' memoir about overcoming adversity and self-discipline.', 15, 95),
            ('Start With Why', 'Simon Sinek\'s exploration of what makes great leaders inspire action.', 13, 105),
            ('Zero to One', 'Peter Thiel\'s notes on startups and building the future.', 14, 90),
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

    def handle(self, *args, **options):
        # Ensure all categories exist
        cat_objects = {}
        for cat_name in self.CATALOG:
            cat, _ = Category.objects.get_or_create(name=cat_name)
            cat_objects[cat_name] = cat
        self.stdout.write(self.style.SUCCESS(f'Ensured {len(cat_objects)} categories exist.'))

        # Delete ALL products for a clean slate before populating
        deleted_count, _ = Product.objects.all().delete()
        self.stdout.write(self.style.WARNING(f'Cleared {deleted_count} existing products.'))

        created = 0
        for cat_name, products in self.CATALOG.items():
            category = cat_objects[cat_name]
            for name, description, base_price, base_stock in products:
                price = round(base_price * random.uniform(0.9, 1.1), 2)
                stock = random.randint(max(1, base_stock - 20), base_stock + 20)
                base_slug = slugify(name)
                slug = base_slug
                i = 1
                while Product.objects.filter(slug=slug).exists():
                    slug = f'{base_slug}-{i}'
                    i += 1
                Product.objects.create(
                    name=name,
                    description=description,
                    price=price,
                    stock=stock,
                    category=category,
                    slug=slug,
                    is_sample=True,
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done. Created {created} sample products across {len(cat_objects)} categories. '
            f'Total products in shop: {Product.objects.count()}'
        ))
