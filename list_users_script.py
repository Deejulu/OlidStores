import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_stores.settings_local_sqlite')
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
for u in User.objects.all():
    print(f"Username: {u.username}, Email: {u.email}, Role: {getattr(u, 'role', 'N/A')}, Is Staff: {u.is_staff}, Is Superuser: {u.is_superuser}")
