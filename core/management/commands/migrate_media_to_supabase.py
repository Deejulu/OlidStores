"""
Management command to migrate local media files to Supabase Storage.
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files import File
from products.models import Product


class Command(BaseCommand):
    help = 'Migrate local media files to Supabase Storage'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually uploading',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No files will be uploaded'))
        
        self.stdout.write('\n=== Migrating Product Images to Supabase ===\n')
        
        # Get all products with images
        products = Product.objects.filter(image__isnull=False).exclude(image='')
        total = products.count()
        
        self.stdout.write(f'Found {total} products with images\n')
        
        migrated = 0
        skipped = 0
        errors = 0
        
        for product in products:
            image_path = product.image.name
            local_path = os.path.join(settings.MEDIA_ROOT, image_path)
            
            # Check if file exists locally
            if not os.path.exists(local_path):
                self.stdout.write(
                    self.style.WARNING(f'⚠ {product.name}: Local file not found: {local_path}')
                )
                skipped += 1
                continue
            
            # Check if already exists in Supabase
            if default_storage.exists(image_path):
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {product.name}: Already in Supabase ({image_path})')
                )
                skipped += 1
                continue
            
            # Upload to Supabase
            if not dry_run:
                try:
                    with open(local_path, 'rb') as local_file:
                        # Save to Supabase
                        saved_name = default_storage.save(image_path, File(local_file))
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ {product.name}: Uploaded to {saved_name}')
                        )
                        migrated += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ {product.name}: Failed to upload: {str(e)}')
                    )
                    errors += 1
            else:
                self.stdout.write(f'  Would upload: {image_path}')
                migrated += 1
        
        # Summary
        self.stdout.write('\n=== Migration Summary ===')
        self.stdout.write(f'Total products: {total}')
        self.stdout.write(self.style.SUCCESS(f'Migrated: {migrated}'))
        self.stdout.write(self.style.WARNING(f'Skipped: {skipped}'))
        if errors > 0:
            self.stdout.write(self.style.ERROR(f'Errors: {errors}'))
        
        if dry_run:
            self.stdout.write('\nRun without --dry-run to actually upload files')
