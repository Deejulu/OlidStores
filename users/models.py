from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from products.models import Product

# ...existing code...

class Feedback(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
	message = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)
	is_resolved = models.BooleanField(default=False)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"Feedback from {self.user.username if self.user else 'Anonymous'} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from products.models import Product
import random
import string

class CustomUser(AbstractUser):
	ROLE_CHOICES = [
		('customer', 'Customer'),
		('admin', 'Admin'),
	]
	# Default role should be 'customer' for new users
	role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
	phone = models.CharField(
		max_length=20,
		unique=True,
		null=True,
		blank=True,
		default=None,
		help_text='Phone number for delivery updates'
	)
	
	# Verification fields
	email_verified = models.BooleanField(default=False, help_text='Has the user verified their email?')
	phone_verified = models.BooleanField(default=True, help_text='Phone verification (auto-verified)')  # Auto-verified since we skip phone OTP
	
	@property
	def is_fully_verified(self):
		"""Check if email is verified (phone is optional)."""
		return self.email_verified
	
	@property
	def needs_verification(self):
		"""Check if user still needs to verify email."""
		return not self.email_verified

class Profile(models.Model):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	address = models.TextField(blank=True)
	whatsapp = models.CharField(max_length=20, blank=True)
	avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

	def __str__(self):
		return f"Profile for {self.user.username}"

class Wishlist(models.Model):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	products = models.ManyToManyField(Product, related_name='wishlisted_by')

	def __str__(self):
		return f"Wishlist for {self.user.username}"

class Address(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='addresses')
	full_name = models.CharField(max_length=100)
	phone = models.CharField(max_length=20)
	address_line = models.TextField()
	is_default = models.BooleanField(default=False)

	def __str__(self):
		return f"Address for {self.user.username}"


class OTPVerification(models.Model):
	"""Store OTP codes for email and phone verification."""
	OTP_TYPE_CHOICES = [
		('email', 'Email Verification'),
		('phone', 'Phone Verification'),
	]
	
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='otp_verifications',
		null=True,
		blank=True
	)
	# For registration before user is created
	email = models.EmailField(blank=True, default='')
	phone = models.CharField(max_length=20, blank=True, default='')
	
	otp_type = models.CharField(max_length=10, choices=OTP_TYPE_CHOICES)
	otp_code = models.CharField(max_length=6)
	created_at = models.DateTimeField(auto_now_add=True)
	expires_at = models.DateTimeField()
	is_verified = models.BooleanField(default=False)
	attempts = models.PositiveIntegerField(default=0)
	
	class Meta:
		ordering = ['-created_at']
		verbose_name = 'OTP Verification'
		verbose_name_plural = 'OTP Verifications'
	
	def __str__(self):
		return f"{self.otp_type} OTP for {self.email or self.phone}"
	
	@classmethod
	def generate_otp(cls):
		"""Generate a 6-digit OTP code."""
		return ''.join(random.choices(string.digits, k=6))
	
	@classmethod
	def create_otp(cls, otp_type, email=None, phone=None, user=None, expiry_minutes=10):
		"""Create a new OTP for verification."""
		# Invalidate any existing OTPs for this email/phone
		if email:
			cls.objects.filter(email=email, otp_type=otp_type, is_verified=False).delete()
		if phone:
			cls.objects.filter(phone=phone, otp_type=otp_type, is_verified=False).delete()
		
		return cls.objects.create(
			user=user,
			email=email or '',
			phone=phone or '',
			otp_type=otp_type,
			otp_code=cls.generate_otp(),
			expires_at=timezone.now() + timedelta(minutes=expiry_minutes)
		)
	
	def is_expired(self):
		"""Check if OTP has expired."""
		return timezone.now() > self.expires_at
	
	def is_valid(self):
		"""Check if OTP can still be used."""
		return not self.is_verified and not self.is_expired() and self.attempts < 5
	
	def verify(self, code):
		"""Attempt to verify the OTP code."""
		self.attempts += 1
		self.save()
		
		if not self.is_valid():
			return False, 'OTP expired or too many attempts'
		
		if self.otp_code == code:
			self.is_verified = True
			self.save()
			return True, 'Verified successfully'
		
		return False, f'Invalid OTP. {5 - self.attempts} attempts remaining'
