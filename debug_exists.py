import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_stores.settings')
django.setup()

import requests
from django.core.files.storage import default_storage

path = 'products/poster.jpg'
print(f'Testing path: {path}')
print(f'Storage exists(): {default_storage.exists(path)}')

url = default_storage.url(path)
print(f'Generated URL: {url}')

r = requests.head(url)
print(f'HEAD request status: {r.status_code}')
print(f'File actually accessible: {r.status_code == 200}')
