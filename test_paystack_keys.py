"""
Quick script to verify Paystack keys are loaded correctly
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_stores.settings')
django.setup()

from django.conf import settings

print("=" * 60)
print("PAYSTACK CONFIGURATION CHECK")
print("=" * 60)

# Check public key
public_key = settings.PAYSTACK_PUBLIC
print(f"\n✓ Public Key: {public_key[:15]}...{public_key[-10:]}")
print(f"  Type: {'LIVE' if public_key.startswith('pk_live_') else 'TEST'}")

# Check secret key
secret_key = settings.PAYSTACK_SECRET
print(f"\n✓ Secret Key: {secret_key[:15]}...{secret_key[-10:]}")
print(f"  Type: {'LIVE' if secret_key.startswith('sk_live_') else 'TEST'}")

# Verify both are live keys
if public_key.startswith('pk_live_') and secret_key.startswith('sk_live_'):
    print("\n" + "=" * 60)
    print("✅ SUCCESS! Live Paystack keys are properly configured!")
    print("=" * 60)
    print("\n⚠️  WARNING: You are using LIVE keys - real money will be charged!")
    print("💡 TIP: Test with a small amount first (e.g., ₦100)")
else:
    print("\n" + "=" * 60)
    print("⚠️  WARNING: You are still using TEST keys")
    print("=" * 60)

print("\nNext steps:")
print("1. Start Django server: python manage.py runserver")
print("2. Visit: http://127.0.0.1:8000")
print("3. Add a product to cart and test checkout")
print("4. Use a real debit card for payment")
print("=" * 60)
