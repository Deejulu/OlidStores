from django.core.management.base import BaseCommand
from django.conf import settings
import os
from PIL import Image, ImageDraw, ImageFont

class Command(BaseCommand):
    help = 'Create default static placeholder images for hero placeholders (saved to static/images/products)'

    def handle(self, *args, **options):
        dest = os.path.join(settings.BASE_DIR, 'static', 'images', 'products')
        os.makedirs(dest, exist_ok=True)
        defs = [
            ('smartphone-display.jpg', '#0f172a', 'Smartphone'),
            ('cosmetics-display.jpg', '#7c3aed', 'Cosmetics'),
            ('fashion-display.jpg', '#ff6b6b', 'Fashion')
        ]
        created = 0
        for fn, color, text in defs:
            path = os.path.join(dest, fn)
            if not os.path.exists(path):
                img = Image.new('RGB', (600, 600), color)
                d = ImageDraw.Draw(img)
                try:
                    fnt = ImageFont.truetype('arial.ttf', 40)
                except Exception:
                    fnt = ImageFont.load_default()
                bbox = d.textbbox((0,0), text, font=fnt)
                w = bbox[2]-bbox[0]; h = bbox[3]-bbox[1]
                d.text(((600-w)/2, (600-h)/2), text, font=fnt, fill='white')
                img.save(path, 'JPEG')
                created += 1
        self.stdout.write(self.style.SUCCESS(f'Created {created} placeholder(s)'))
