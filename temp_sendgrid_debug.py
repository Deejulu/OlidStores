import os
import traceback

print("ENV VARS")
for key in [
    "EMAIL_BACKEND",
    "SENDGRID_API_KEY",
    "SENDGRID_SENDER_EMAIL",
    "SENDGRID_SENDER_NAME",
    "DEFAULT_FROM_EMAIL",
    "OTP_DEBUG_MODE",
]:
    print(f"{key}={repr(os.getenv(key))}")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "e_stores.settings")

import django
from django.conf import settings
from django.core.mail import send_mail

django.setup()

print("\nDJANGO SETTINGS")
print("settings.EMAIL_BACKEND:", settings.EMAIL_BACKEND)
print("settings.SENDGRID_API_KEY set:", bool(getattr(settings, "SENDGRID_API_KEY", "")))
print("settings.SENDGRID_SENDER_EMAIL:", getattr(settings, "SENDGRID_SENDER_EMAIL", ""))
print("settings.DEFAULT_FROM_EMAIL:", settings.DEFAULT_FROM_EMAIL)
print("settings.OTP_DEBUG_MODE:", getattr(settings, "OTP_DEBUG_MODE", None))

try:
    result = send_mail(
        "E-Stores SendGrid Debug Test",
        "This is a SendGrid debug test email.",
        settings.SENDGRID_SENDER_EMAIL,
        [settings.SENDGRID_SENDER_EMAIL],
        fail_silently=False,
    )
    print("send_mail result:", result)
except Exception:
    print("\nEXCEPTION RAISED:")
    traceback.print_exc()
