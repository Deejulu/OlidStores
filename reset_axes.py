import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_stores.settings_local_sqlite')

import django
django.setup()

from axes.models import AccessAttempt, AccessLog

AccessAttempt.objects.all().delete()
AccessLog.objects.all().delete()

print("Axes lockout cleared.")
