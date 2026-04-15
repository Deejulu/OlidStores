import os
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_stores.settings')

print('EMAIL_BACKEND env:', os.environ.get('EMAIL_BACKEND'))
print('SENDGRID_API_KEY env set:', bool(os.environ.get('SENDGRID_API_KEY')))
print('SENDGRID_SENDER_EMAIL env:', os.environ.get('SENDGRID_SENDER_EMAIL'))
print('SENDGRID_SENDER_NAME env:', os.environ.get('SENDGRID_SENDER_NAME'))
print('DEFAULT_FROM_EMAIL env:', os.environ.get('DEFAULT_FROM_EMAIL'))

try:
    import django
    django.setup()
    from django.conf import settings
    from django.core.mail import send_mail

    print('settings.EMAIL_BACKEND:', settings.EMAIL_BACKEND)
    print('settings.SENDGRID_API_KEY set:', bool(getattr(settings, 'SENDGRID_API_KEY', '')))
    print('settings.SENDGRID_SENDER_EMAIL:', getattr(settings, 'SENDGRID_SENDER_EMAIL', ''))
    print('settings.DEFAULT_FROM_EMAIL:', settings.DEFAULT_FROM_EMAIL)

    try:
        result = send_mail(
            'E-Stores SendGrid Test',
            'This is a SendGrid test.',
            settings.SENDGRID_SENDER_EMAIL,
            [settings.SENDGRID_SENDER_EMAIL],
            fail_silently=False,
        )
        print('send_mail result:', result)
    except Exception:
        traceback.print_exc()
except Exception:
    traceback.print_exc()
