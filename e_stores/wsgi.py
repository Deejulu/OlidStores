import os
import threading
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_stores.settings')
application = get_wsgi_application()


def _create_or_update_admin_user():
    username = os.getenv('DJANGO_ADMIN_USERNAME')
    password = os.getenv('DJANGO_ADMIN_PASSWORD')
    if not username or not password:
        return

    # Only create/update admin in production-style deployments.
    if os.getenv('DJANGO_DEBUG', 'True').lower() in ('1', 'true', 'yes'):
        return

    email = os.getenv('DJANGO_ADMIN_EMAIL', 'admin@example.com')
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admin = User.objects.filter(is_superuser=True).first()
        if admin:
            changed = False
            if admin.username != username:
                admin.username = username
                changed = True
            if admin.email != email:
                admin.email = email
                changed = True
            if not admin.check_password(password):
                admin.set_password(password)
                changed = True
            if not admin.is_staff:
                admin.is_staff = True
                changed = True
            if not admin.is_superuser:
                admin.is_superuser = True
                changed = True
            if changed:
                admin.save()
        else:
            User.objects.create_superuser(username=username, email=email, password=password)
    except Exception:
        # Ignore failures during startup if migrations are not yet applied.
        pass

threading.Thread(target=_create_or_update_admin_user, daemon=True).start()
