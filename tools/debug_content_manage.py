import django
django.setup()
from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from core.models import SiteContent
User = get_user_model()
admin = User.objects.create_superuser(username='tmpadmin', email='tmp@example.com', password='pass')
admin.role='admin'
admin.is_staff=True
admin.is_superuser=True
admin.save()
client = Client()
client.force_login(admin)
resp = client.post(reverse('admin_dashboard:content_manage'), {
    'about-title': 'About',
    'about-content': 'About',
    'about-key': 'about',
    'contact-key': 'contact',
    'banner-key': 'homepage_banner',
    'checkout-key': 'checkout',
    'checkout-title': 'Checkout',
    'checkout-content': 'Checkout info',
    'checkout-delivery_fee_24h': '33.50',
    'checkout-delivery_fee_2d': '12.00',
    'bimgs-TOTAL_FORMS': '0',
    'bimgs-INITIAL_FORMS': '0',
    'heros-TOTAL_FORMS': '0',
    'heros-INITIAL_FORMS': '0',
})
print('status', resp.status_code)
text = resp.content.decode('utf-8')
print('len content', len(text))
idx = text.find('delivery_fee_24h')
print('index of delivery_fee_24h in response:', idx)
print('snippet:', text[idx-200:idx+200])
sc = SiteContent.objects.filter(key='checkout').first()
print('sitecontent exists:', sc is not None)
print('delivery_fee_24h:', sc.delivery_fee_24h, 'delivery_fee_2d:', sc.delivery_fee_2d)
