from django.core.management.base import BaseCommand
from django.conf import settings
import os
from PIL import Image, ImageDraw, ImageFont
from core.models import HeroImage

class Command(BaseCommand):
    help = 'Creates sample hero images and HeroImage records'

    def handle(self, *args, **options):
        dest = os.path.join(settings.MEDIA_ROOT, 'hero')
        os.makedirs(dest, exist_ok=True)
        colors = ['#1e3a8a', '#9a3412', '#065f46']
        created = 0
        for i, color in enumerate(colors, start=1):
            filename = f'hero_sample_{i}.jpg'
            path = os.path.join(dest, filename)
            if not os.path.exists(path):
                img = Image.new('RGB', (500, 500), color)
                d = ImageDraw.Draw(img)
                text = f'Hero {i}'
                try:
                    fnt = ImageFont.truetype('arial.ttf', 40)
                except Exception:
                    fnt = ImageFont.load_default()
                bbox = d.textbbox((0,0), text, font=fnt)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                d.text(((500-text_w)/2, (500-text_h)/2), text, font=fnt, fill='white')
                img.save(path, 'JPEG')
            rel_path = os.path.join('hero', filename)
            if not HeroImage.objects.filter(image=rel_path).exists():
                HeroImage.objects.create(title=f'Sample Hero {i}', image=rel_path, order=i, is_active=True)
                created += 1
        self.stdout.write(self.style.SUCCESS(f'Created {created} sample hero image(s)'))
