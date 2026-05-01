import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from products.models import Product

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Debug storage configuration and test image URL generation'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Storage Configuration Debug ===\n'))
        
        # Print storage settings
        self.stdout.write(f"DEFAULT_FILE_STORAGE: {settings.DEFAULT_FILE_STORAGE}")
        self.stdout.write(f"MEDIA_URL: {settings.MEDIA_URL}")
        self.stdout.write(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
        
        # Check Supabase configuration
        if hasattr(settings, 'SUPABASE_URL'):
            self.stdout.write(f"\nSupabase URL: {settings.SUPABASE_URL}")
            self.stdout.write(f"Supabase Bucket: {getattr(settings, 'SUPABASE_STORAGE_BUCKET', 'Not set')}")
            self.stdout.write(f"Service Role Key: {'Set' if getattr(settings, 'SUPABASE_SERVICE_ROLE_KEY', None) else 'Not set'}")
        
        # Check AWS/S3 configuration
        if hasattr(settings, 'AWS_STORAGE_BUCKET_NAME'):
            self.stdout.write(f"\nAWS Bucket: {settings.AWS_STORAGE_BUCKET_NAME}")
            self.stdout.write(f"AWS Region: {getattr(settings, 'AWS_S3_REGION_NAME', 'Not set')}")
            self.stdout.write(f"AWS Endpoint: {getattr(settings, 'AWS_S3_ENDPOINT_URL', 'Default')}")
            self.stdout.write(f"AWS Access Key: {'Set' if getattr(settings, 'AWS_ACCESS_KEY_ID', None) else 'Not set'}")
        
        # Test image URL generation
        self.stdout.write(self.style.SUCCESS('\n=== Testing Image URL Generation ===\n'))
        
        products_with_images = Product.objects.exclude(image='').exclude(image__isnull=True)[:5]
        
        if not products_with_images:
            self.stdout.write(self.style.WARNING('No products with images found in database'))
        else:
            for product in products_with_images:
                self.stdout.write(f"\nProduct: {product.name} (ID: {product.id})")
                self.stdout.write(f"  Image field value: {product.image.name}")
                try:
                    url = product.image.url
                    self.stdout.write(self.style.SUCCESS(f"  Generated URL: {url}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  Error generating URL: {str(e)}"))
                
                # Try to check if file exists (only works for local storage)
                if settings.DEFAULT_FILE_STORAGE == 'django.core.files.storage.FileSystemStorage':
                    try:
                        exists = product.image.storage.exists(product.image.name)
                        self.stdout.write(f"  File exists: {exists}")
                        if exists:
                            size = product.image.size
                            self.stdout.write(f"  File size: {size} bytes")
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"  Could not check existence: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS('\n=== Debug Complete ===\n'))
