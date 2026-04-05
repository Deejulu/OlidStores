import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_stores.settings')
django.setup()

from core.models import SiteContent

# Get or create checkout SiteContent
checkout, created = SiteContent.objects.get_or_create(key='checkout')

# Set default bank details if not already set
if not checkout.bank_name:
    checkout.bank_name = 'GTBank'
if not checkout.account_name:
    checkout.account_name = 'E-Stores Ltd'
if not checkout.account_number:
    checkout.account_number = '0123456789'

checkout.save()
print(f"✓ Bank transfer details {'created' if created else 'updated'} for checkout section")
print(f"  Bank Name: {checkout.bank_name}")
print(f"  Account Name: {checkout.account_name}")
print(f"  Account Number: {checkout.account_number}")
