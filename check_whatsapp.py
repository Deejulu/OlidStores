import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_stores.settings')
django.setup()

from core.context_processors import site_contact
from django.test import RequestFactory

# Create a fake request
factory = RequestFactory()
request = factory.get('/')

# Call the context processor
context = site_contact(request)

print(f"Contact WhatsApp URL: {context.get('contact_whatsapp')}")
print(f"Contact Email: {context.get('contact_email')}")
print(f"\nAll social items:")
for item in context.get('contact_social_list', []):
    print(f"  {item['platform']}: {item['url']}")
