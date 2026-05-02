import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_stores.settings')
django.setup()

from django.core.files.storage import default_storage
from django.conf import settings

print(f'DEFAULT_FILE_STORAGE setting: {settings.DEFAULT_FILE_STORAGE}')
print(f'default_storage class: {default_storage.__class__}')
print(f'default_storage instance: {default_storage}')
print(f'Is SupabaseStorage: {"SupabaseStorage" in str(default_storage.__class__)}')
