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
		indexes = [
			models.Index(fields=['is_resolved', '-created_at'], name='feedback_resolved_created'),
		]

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
import secrets

class CustomUser(AbstractUser):
	ROLE_CHOICES = [
		('customer', 'Customer'),
		('admin', 'Admin'),
	]
	# Default role should be 'customer' for new users
	role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
	phone = models.CharField(
		max_length=20,
		blank=True,
		null=True,
		unique=True,
		default=None,
		help_text='Phone number for delivery updates'
	)
	
	# Verification fields
	email_verified = models.BooleanField(default=False, help_text='Has the user verified their email?')
	phone_verified = models.BooleanField(default=True, help_text='Phone verification (auto-verified)')  # Auto-verified since we skip phone OTP
	
	# Account ID - cryptographically random identifier, separate from username
	account_id = models.CharField(
		max_length=12,
		unique=True,
		null=True,
		blank=True,
		db_index=True,
		help_text='Cryptographic random account identifier'
	)

	# Sample data flag
	is_sample = models.BooleanField(default=False, db_index=True, help_text='Marks users created by the sample data tool')
	
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
	otp_code_hash = models.CharField(max_length=128, null=True)
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
		"""Create a new OTP for verification.

		Returns the OTP instance. The plaintext OTP is NOT stored;
		only a hash is kept. Use the returned instance's `plaintext_code`
		attribute to send the code to the user.
		"""
		# Invalidate any existing OTPs for this email/phone
		if email:
			cls.objects.filter(email=email, otp_type=otp_type, is_verified=False).delete()
		if phone:
			cls.objects.filter(phone=phone, otp_type=otp_type, is_verified=False).delete()

		# Generate plaintext code for sending (not stored)
		plaintext_code = cls.generate_otp()

		instance = cls.objects.create(
			user=user,
			email=email or '',
			phone=phone or '',
			otp_type=otp_type,
			otp_code_hash=cls._hash_otp(plaintext_code),
			expires_at=timezone.now() + timedelta(minutes=expiry_minutes)
		)
		# Attach plaintext code for one-time use (sending to user)
		instance.plaintext_code = plaintext_code
		return instance

	@staticmethod
	def _hash_otp(code):
		"""Hash an OTP code using Django's password hashing."""
		from django.contrib.auth.hashers import make_password
		return make_password(code)

	@staticmethod
	def _check_otp(code, code_hash):
		"""Verify an OTP code against its hash."""
		from django.contrib.auth.hashers import check_password
		return check_password(code, code_hash)

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

		if self._check_otp(code, self.otp_code_hash):
			self.is_verified = True
			self.save()
			return True, 'Verified successfully'

		return False, f'Invalid OTP. {5 - self.attempts} attempts remaining'


class SecurityQuestion(models.Model):
	"""Static security questions for account recovery."""
	QUESTION_CHOICES = [
		('pet_name', 'What is the name of your first pet?'),
		('fav_color', 'What is your favorite color?'),
		('best_friend', 'What is the name of your best friend?'),
		('fav_food', 'What is your favorite food?'),
		('fav_book', 'What is your favorite book or author?'),
		('childhood_hero', 'What is the name of your childhood hero?'),
		('childhood_street', 'What is the name of the street you grew up on?'),
		('fav_movie', 'What is your favorite movie of all time?'),
		('first_teacher', 'What is the name of your first teacher?'),
		('fav_vacation', 'What is your favorite vacation destination?'),
		('fav_childhood_memory', 'What is your favorite childhood memory?'),
		('fav_athlete', 'What is the name of your favorite athlete or sports team?'),
		('fav_restaurant', 'What is the name of your favorite restaurant or meal?'),
		('dream_job', 'What is your dream job or career?'),
		('first_school', 'What is the name of the first school you attended?'),
		('fav_song', 'What is your favorite song or artist?'),
		('first_car', 'What is the name of your first car?'),
		('fav_tradition', 'What is your favorite family tradition?'),
		('closest_relative', 'What is the name of your closest relative?'),
		('mother_maiden', 'What is your mother\'s maiden name?'),
		('birth_city', 'In what city were you born?'),
		('school_name', 'What was the name of your elementary school?'),
		('fav_teacher', 'Who was your favorite teacher?'),
		('birth_month', 'In what month was your father born?'),
		('childhood_friend', 'What was the name of your childhood best friend?'),
	]
	
	question_key = models.CharField(max_length=50, unique=True, choices=QUESTION_CHOICES)
	question_text = models.CharField(max_length=255)
	
	class Meta:
		ordering = ['question_key']
	
	def __str__(self):
		return self.question_text


class SecurityAnswer(models.Model):
	"""Hashed security answers for account recovery."""
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='security_answers'
	)
	question = models.ForeignKey(SecurityQuestion, on_delete=models.CASCADE)
	answer_hash = models.CharField(max_length=255, help_text='Hashed answer (one-way)')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	
	class Meta:
		unique_together = ['user', 'question']
		ordering = ['user', 'question']
	
	def __str__(self):
		return f"Security answer for {self.user.username}"
