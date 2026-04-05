from django.core.management.base import BaseCommand
from django.conf import settings
import os
from PIL import Image, ImageDraw, ImageFont
from core.models import BannerImage

class Command(BaseCommand):
    help = 'Creates sample banner images and BannerImage records'

    def handle(self, *args, **options):
        dest = os.path.join(settings.MEDIA_ROOT, 'banners')
        os.makedirs(dest, exist_ok=True)
        colors = ['#4f46e5', '#ff6b6b']
        created = 0
        for i, color in enumerate(colors, start=1):
            filename = f'banner_sample_{i}.jpg'
            path = os.path.join(dest, filename)
            if not os.path.exists(path):
                img = Image.new('RGB', (1200, 400), color)
                d = ImageDraw.Draw(img)
                text = f'Promo {i} - E-Stores'
                try:
                    fnt = ImageFont.truetype('arial.ttf', 60)
                except Exception:
                    fnt = ImageFont.load_default()
                try:
                    text_w, text_h = d.textsize(text, font=fnt)
                except AttributeError:
                    bbox = d.textbbox((0,0), text, font=fnt)
                    text_w = bbox[2] - bbox[0]
                    text_h = bbox[3] - bbox[1]
                d.text(((1200-text_w)/2, (400-text_h)/2), text, font=fnt, fill='white')
                img.save(path, 'JPEG')
            rel_path = os.path.join('banners', filename)
            if not BannerImage.objects.filter(image=rel_path).exists():
                BannerImage.objects.create(title=f'Sample Banner {i}', image=rel_path, order=i, is_active=True)
                created += 1
        self.stdout.write(self.style.SUCCESS(f'Created {created} sample banner(s)'))
