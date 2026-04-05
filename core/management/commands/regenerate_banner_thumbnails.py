from django.core.management.base import BaseCommand
from core.models import BannerImage, HeroImage
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Regenerate resized images and thumbnails for BannerImage and HeroImage records. Uses model._process_image() to reprocess.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, help='Limit number of images to process')
        parser.add_argument('--dry-run', action='store_true', help='Show which images would be processed without saving')
        parser.add_argument('--models', type=str, help='Comma-separated list of models to process: banner,hero (default both)')

    def handle(self, *args, **options):
        models = options.get('models')
        target = []
        if not models:
            target = [('banner', BannerImage.objects.all().order_by('order', '-created_at')),
                      ('hero', HeroImage.objects.all().order_by('order', '-created_at'))]
        else:
            models = [m.strip().lower() for m in models.split(',')]
            if 'banner' in models:
                target.append(('banner', BannerImage.objects.all().order_by('order', '-created_at')))
            if 'hero' in models:
                target.append(('hero', HeroImage.objects.all().order_by('order', '-created_at')))

        limit = options.get('limit')
        processed = 0
        for name, qs in target:
            if limit:
                qs = qs[:limit]
            for b in qs:
                b.refresh_from_db()
                self.stdout.write(f'Processing {name} id={b.id} title="{b.title}" image={b.image}')
                if options.get('dry_run'):
                    continue
                try:
                    ok = b._process_image()
                    if ok:
                        b.save()
                        processed += 1
                    else:
                        self.stderr.write(f'Skipped {b.id}: no image to process')
                except Exception as e:
                    self.stderr.write(f'Failed to process {b.id}: {e}')
        self.stdout.write(self.style.SUCCESS(f'Regenerated {processed} image(s)'))
