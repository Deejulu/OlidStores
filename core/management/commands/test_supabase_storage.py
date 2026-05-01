"""Test Supabase storage connectivity"""
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.conf import settings
from e_stores.storage_backends import SupabaseStorage


class Command(BaseCommand):
    help = 'Test Supabase storage connectivity'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Testing Supabase Storage ===\n'))
        
        try:
            # Initialize storage
            storage = SupabaseStorage()
            self.stdout.write(f"✓ Storage initialized")
            self.stdout.write(f"  Bucket: {storage.bucket_name}")
            self.stdout.write(f"  Base URL: {storage.base_url}")
            
            # Test uploading a small test image (1x1 transparent PNG)
            test_filename = 'test/test.png'
            # Minimal 1x1 transparent PNG
            png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
            test_content = ContentFile(png_data)
            test_content.name = 'test.png'
            
            self.stdout.write(f"\nTesting upload...")
            saved_name = storage.save(test_filename, test_content)
            self.stdout.write(self.style.SUCCESS(f"✓ File uploaded: {saved_name}"))
            
            # Test file existence
            self.stdout.write(f"\nTesting existence check...")
            exists = storage.exists(saved_name)
            self.stdout.write(self.style.SUCCESS(f"✓ File exists: {exists}"))
            
            # Test URL generation
            self.stdout.write(f"\nTesting URL generation...")
            url = storage.url(saved_name)
            self.stdout.write(self.style.SUCCESS(f"✓ URL generated: {url}"))
            
            # Test file size
            self.stdout.write(f"\nTesting size retrieval...")
            size = storage.size(saved_name)
            self.stdout.write(self.style.SUCCESS(f"✓ File size: {size} bytes"))
            
            # Test deletion
            self.stdout.write(f"\nTesting deletion...")
            storage.delete(saved_name)
            exists_after = storage.exists(saved_name)
            self.stdout.write(self.style.SUCCESS(f"✓ File deleted (exists after: {exists_after})"))
            
            self.stdout.write(self.style.SUCCESS('\n✓ All tests passed! Supabase storage is working!\n'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Test failed: {str(e)}\n'))
            import traceback
            self.stdout.write(traceback.format_exc())
