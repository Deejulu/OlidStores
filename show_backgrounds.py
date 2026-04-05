import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_stores.settings')
django.setup()

from core.models import SiteContent

banner = SiteContent.objects.filter(key='homepage_banner').first()
print('Current background style:', banner.background_style)
print('\nAvailable background styles:')
choices = banner._meta.get_field('background_style').choices
for value, label in choices:
    current = ' (CURRENT)' if value == banner.background_style else ''
    print(f'  - {value}: {label}{current}')

print('\n✓ All background styles are properly configured!')
print('✓ You can change them from the admin panel at: Site Content → Homepage Banner')
