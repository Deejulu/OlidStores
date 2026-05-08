"""
Test OTP email sending with real SendGrid credentials
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_stores.settings')
django.setup()

from users.otp_utils import send_email_otp
from django.conf import settings

print("="*60)
print("TESTING OTP EMAIL CONFIGURATION")
print("="*60)
print(f"\nConfiguration:")
print(f"  OTP_DEBUG_MODE: {settings.OTP_DEBUG_MODE}")
print(f"  EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
print(f"  DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
print(f"  SENDGRID API Key: {settings.SENDGRID_API_KEY[:10]}...")

print(f"\nSending test OTP email to: daveed0011@gmail.com")
print(f"Test OTP Code: 123456")
print("-"*60)

success, error = send_email_otp('daveed0011@gmail.com', '123456', 'email_verification')

print("\n" + "="*60)
if success:
    print("✅ SUCCESS! Email sent successfully!")
    print("\nCheck your inbox at: daveed0011@gmail.com")
    print("Subject: Your E-Stores Verification Code: 123456")
    print("\nIf you don't see it:")
    print("  1. Check your spam/junk folder")
    print("  2. Wait 1-2 minutes (SendGrid can be slow)")
    print("  3. Verify daveed0011@gmail.com is a valid sender in SendGrid")
else:
    print("❌ FAILED to send email!")
    print(f"\nError: {error}")
    print("\nPossible issues:")
    print("  1. SendGrid API key is invalid")
    print("  2. Sender email not verified in SendGrid")
    print("  3. SendGrid account suspended/inactive")
print("="*60)
