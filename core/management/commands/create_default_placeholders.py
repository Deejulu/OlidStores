from django.core.management.base import BaseCommand
from django.conf import settings
import os
from PIL import Image, ImageDraw, ImageFont

class Command(BaseCommand):
    help = 'Create default static placeholder images used by the front page (static/images/products)'

    def handle(self, *args, **options):
        dest = os.path.join(settings.BASE_DIR, 'static', 'images', 'products')
        os.makedirs(dest, exist_ok=True)
        specs = [
            ('smartphone-display.jpg', '#0f172a', 'Smartphone'),
            ('cosmetics-display.jpg', '#6b21a8', 'Cosmetics'),
            ('fashion-display.jpg', '#065f46', 'Fashion'),
        ]
        created = 0
        for fname, color, label in specs:
            path = os.path.join(dest, fname)
            if not os.path.exists(path):
                img = Image.new('RGB', (600, 400), color)
                d = ImageDraw.Draw(img)
                text = label
                try:
                    fnt = ImageFont.truetype('arial.ttf', 40)
                except Exception:
                    fnt = ImageFont.load_default()
                bbox = d.textbbox((0,0), text, font=fnt)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                d.text(((600-text_w)/2, (400-text_h)/2), text, font=fnt, fill='white')
                img.save(path, 'JPEG')
                created += 1
        self.stdout.write(self.style.SUCCESS(f'Created {created} placeholder image(s) in static/images/products'))
