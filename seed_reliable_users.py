import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_stores.settings_local_sqlite')

import django
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Ensure admin exists with known credentials
admin, created = User.objects.get_or_create(
    username='localadmin',
    defaults={'email': 'admin@local.test', 'is_staff': True, 'is_superuser': True, 'role': 'admin'},
)
admin.set_password('AdminPass123!')
admin.is_staff = True
admin.is_superuser = True
admin.role = 'admin'
admin.is_active = True
admin.save()

print(f"Admin ready: username=localadmin password=AdminPass123! created={created}")

# Ensure customer exists with known credentials
customer, created = User.objects.get_or_create(
    username='localcustomer',
    defaults={'email': 'customer@local.test', 'role': 'customer'},
)
customer.set_password('CustomerPass123!')
customer.role = 'customer'
customer.is_active = True
customer.save()

print(f"Customer ready: username=localcustomer password=CustomerPass123! created={created}")
