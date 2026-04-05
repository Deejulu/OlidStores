from django.db import models


class GalleryImage(models.Model):
	title = models.CharField(max_length=100, blank=True)
	image = models.ImageField(upload_to='gallery/')
	alt_text = models.CharField(max_length=200, blank=True)

	def __str__(self):
		return self.title or "Gallery Image"


# Promotional banner images for the homepage
class BannerImage(models.Model):
	title = models.CharField(max_length=150, blank=True)
	image = models.ImageField(upload_to='banners/')
	thumbnail = models.ImageField(upload_to='banners/thumbs/', blank=True, null=True)
	alt_text = models.CharField(max_length=200, blank=True)
	link = models.URLField(blank=True)
	order = models.IntegerField(default=0, help_text='Lower numbers show first')
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['order', '-created_at']

	def __str__(self):
		return self.title or f"Banner {self.pk}"

	def _process_image(self):
		"""Process and optimize the main image and create a thumbnail for banner images."""
		from PIL import Image, ImageOps
		from io import BytesIO
		from django.core.files.base import ContentFile
		import os
		if not self.image:
			return False
		img = Image.open(self.image)
		img = ImageOps.exif_transpose(img)
		img = img.convert('RGB')
		# Resize main image to max width 1200
		max_w = 1200
		if img.width > max_w:
			ratio = max_w / float(img.width)
			new_h = int(img.height * ratio)
			resized = img.resize((max_w, new_h), Image.LANCZOS)
		else:
			resized = img
		# Save optimized main image (strip EXIF by not passing exif)
		buffer = BytesIO()
		resized.save(buffer, format='JPEG', quality=80, optimize=True, progressive=True)
		file_name = os.path.basename(self.image.name)
		self.image.save(file_name, ContentFile(buffer.getvalue()), save=False)
		# Create thumbnail (max 400px on longest side)
		thumb = resized.copy()
		thumb.thumbnail((400, 400), Image.LANCZOS)
		buf2 = BytesIO()
		thumb.save(buf2, format='JPEG', quality=70, optimize=True)
		thumb_name = f"thumb_{os.path.basename(self.image.name)}"
		self.thumbnail.save(thumb_name, ContentFile(buf2.getvalue()), save=False)
		return True

	def save(self, *args, **kwargs):
		try:
			self._process_image()
		except Exception:
			pass
		super().save(*args, **kwargs)


# Small set of hero images (floating product mockups in hero)
class HeroImage(models.Model):
	title = models.CharField(max_length=150, blank=True)
	image = models.ImageField(upload_to='hero/')
	thumbnail = models.ImageField(upload_to='hero/thumbs/', blank=True, null=True)
	alt_text = models.CharField(max_length=200, blank=True)
	order = models.IntegerField(default=0, help_text='Lower numbers show first')
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['order', '-created_at']

	def __str__(self):
		return self.title or f"Hero {self.pk}"

	def _process_image(self):
		"""Process image and create thumbnail for hero images."""
		from PIL import Image, ImageOps
		from io import BytesIO
		from django.core.files.base import ContentFile
		import os
		if not self.image:
			return False
		img = Image.open(self.image)
		img = ImageOps.exif_transpose(img)
		img = img.convert('RGB')
		# Resize to reasonable size for hero mockups if too large
		max_w = 600
		if img.width > max_w:
			ratio = max_w / float(img.width)
			new_h = int(img.height * ratio)
			resized = img.resize((max_w, new_h), Image.LANCZOS)
		else:
			resized = img
		# Save optimized main image
		buffer = BytesIO()
		resized.save(buffer, format='JPEG', quality=80, optimize=True)
		file_name = os.path.basename(self.image.name)
		self.image.save(file_name, ContentFile(buffer.getvalue()), save=False)
		# Create thumbnail (max 200px)
		thumb = resized.copy()
		thumb.thumbnail((200, 200), Image.LANCZOS)
		buf = BytesIO()
		thumb.save(buf, format='JPEG', quality=70, optimize=True)
		thumb_name = f"thumb_{os.path.basename(self.image.name)}"
		self.thumbnail.save(thumb_name, ContentFile(buf.getvalue()), save=False)
		return True

	def save(self, *args, **kwargs):
		try:
			self._process_image()
		except Exception:
			pass
		super().save(*args, **kwargs)



# Site-wide editable content (About, Contact, Homepage Banner, etc)
class SiteContent(models.Model):
	CONTENT_CHOICES = [
		("about", "About Page"),
		("contact", "Contact Page"),
		("homepage_banner", "Homepage Banner"),
		("checkout", "Checkout Section"),
		("site_settings", "Site Settings"),
		("faq", "FAQ Page"),
		("privacy", "Privacy Policy"),
		("terms", "Terms & Conditions"),
	]
	
	BACKGROUND_STYLE_CHOICES = [
		("gradient_blue", "Dark Blue Gradient (Default)"),
		("gradient_purple", "Purple Gradient"),
		("gradient_orange", "Orange Sunset Gradient"),
		("gradient_green", "Green Gradient"),
		("animated_gradient", "Animated Rainbow Gradient"),
		("particles", "Particle Animation"),
		("waves", "Animated Waves"),
		("sunset_blur", "Sunset Blur (Warm Orbs)"),
		("neon_pulse", "Neon Pulse (Animated Glow)"),
		("stellar_night", "Starlit Night (Stars + Depth)"),
		("video", "Video Background (Upload video file)"),
	]
	
	key = models.CharField(max_length=50, choices=CONTENT_CHOICES, unique=True)
	title = models.CharField(max_length=200, blank=True)
	content = models.TextField(blank=True)
	announcement_text = models.TextField(blank=True, help_text="Top banner announcement text (e.g. 'Free shipping on orders over ₦15,000 | Use code DFLOW10 for 10% off')")
	# Announcement Bar Items (3 rotating items shown in header)
	announcement_bar_item1 = models.CharField(max_length=200, blank=True, default="Free shipping on orders over ₦15,000", help_text="First announcement item (e.g. shipping info)")
	announcement_bar_item2 = models.CharField(max_length=200, blank=True, default="Use code OLID10 for 10% off", help_text="Second announcement item (e.g. promo code)")
	announcement_bar_item3 = models.CharField(max_length=200, blank=True, default="Secure checkout guaranteed", help_text="Third announcement item (e.g. trust message)")
	background_style = models.CharField(max_length=50, choices=BACKGROUND_STYLE_CHOICES, default="gradient_blue", help_text="Choose background style for homepage banner")
	background_video = models.FileField(upload_to='backgrounds/', blank=True, null=True, help_text="Upload video for video background (MP4 format recommended)")
	phone = models.CharField(max_length=30, blank=True)
	email = models.EmailField(blank=True)
	social_links = models.TextField(blank=True, help_text="Comma-separated list of social media links (e.g. https://twitter.com/yourpage, https://facebook.com/yourpage)")
	# Checkout-specific editable fees
	from django.core.validators import MinValueValidator
	delivery_fee_24h = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text='Delivery fee for 24-hour delivery (admin editable)', validators=[MinValueValidator(0)])
	delivery_fee_2d = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text='Delivery fee for 2-day delivery (admin editable)', validators=[MinValueValidator(0)])
	# Manual Payment / Bank Transfer Details (checkout-specific)
	bank_name = models.CharField(max_length=100, blank=True, help_text='Bank name for manual transfer payments (e.g. GTBank, Access Bank)')
	account_name = models.CharField(max_length=200, blank=True, help_text='Account holder name for manual transfers')
	account_number = models.CharField(max_length=50, blank=True, help_text='Account number for manual bank transfers')
	# New structured social handles field. Store platform -> handle or URL, e.g. {"twitter": "@handle", "instagram": "handle", "whatsapp": "080..."}
	try:
		from django.db.models import JSONField
		social = JSONField(blank=True, null=True, default=dict, help_text='JSON object for social handles, e.g. {"twitter":"@you", "instagram":"you", "whatsapp":"080..."}')
	except Exception:
		# Fallback for older Django versions
		social = models.TextField(blank=True, help_text='JSON string of social handles (use a dict with platform keys)')
	map_embed = models.TextField(blank=True, help_text="Embed code for Google Maps or similar")
	
	# ─── Site Settings Fields ───
	site_name = models.CharField(max_length=200, blank=True, help_text='Your store/site name displayed in header and emails')
	site_tagline = models.CharField(max_length=300, blank=True, help_text='A short tagline or slogan for your store')
	site_logo = models.ImageField(upload_to='site/', blank=True, null=True, help_text='Your store logo (recommended: 200x60px or SVG)')
	favicon = models.ImageField(upload_to='site/', blank=True, null=True, help_text='Favicon for browser tabs (32x32 or 64x64 ICO/PNG)')
	footer_text = models.TextField(blank=True, help_text='Custom footer text (copyright, legal info, etc.)')
	store_address = models.TextField(blank=True, help_text='Physical store address for contact page and footer')
	business_hours = models.TextField(blank=True, help_text='Business hours (e.g. Mon-Fri: 9AM-6PM, Sat: 10AM-4PM)')
	
	# ─── Individual Social Media Fields ───
	twitter_handle = models.CharField(max_length=100, blank=True, help_text='Twitter handle (e.g. @yourhandle) or full URL')
	instagram_handle = models.CharField(max_length=100, blank=True, help_text='Instagram handle (e.g. yourhandle) or full URL')
	facebook_handle = models.CharField(max_length=200, blank=True, help_text='Facebook page/handle or full URL')
	whatsapp_number = models.CharField(max_length=30, blank=True, help_text='WhatsApp number (e.g. +2348012345678) or wa.me link')
	tiktok_handle = models.CharField(max_length=100, blank=True, help_text='TikTok handle or full URL')
	youtube_handle = models.CharField(max_length=200, blank=True, help_text='YouTube channel URL')
	
	# ─── Shipping & Policies ───
	free_shipping_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text='Order amount for free shipping (0 = disabled)', validators=[MinValueValidator(0)])
	return_policy_days = models.PositiveIntegerField(default=7, help_text='Number of days for returns/exchanges')
	
	# ─── SEO Fields ───
	meta_description = models.TextField(blank=True, help_text='SEO meta description for this page (150-160 characters recommended)')
	meta_keywords = models.CharField(max_length=500, blank=True, help_text='SEO keywords, comma-separated')
	
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return self.get_key_display()


class ContactMessage(models.Model):
	"""Messages submitted via the Contact page."""
	name = models.CharField(max_length=200)
	email = models.EmailField()
	subject = models.CharField(max_length=200, blank=True)
	message = models.TextField()
	user = models.ForeignKey('users.CustomUser', null=True, blank=True, on_delete=models.SET_NULL)
	ip_address = models.CharField(max_length=45, blank=True)
	is_read = models.BooleanField(default=False)
	# Admin reply fields
	admin_reply = models.TextField(blank=True)
	replied_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	@property
	def is_replied(self):
		return bool(self.admin_reply)

	def __str__(self):
		return f"Contact from {self.name} <{self.email}> - {self.subject[:30]}"


class TeamMember(models.Model):
	"""Optional team members for the About page."""
	name = models.CharField(max_length=150)
	title = models.CharField(max_length=150, blank=True)
	bio = models.TextField(blank=True)
	image = models.ImageField(upload_to='team/', blank=True, null=True)
	social = models.JSONField(blank=True, null=True, default=dict, help_text='Optional social handles e.g. {"twitter":"@you"}')
	order = models.IntegerField(default=0)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['order', 'name']

	def __str__(self):
		return self.name


class ChatConversation(models.Model):
	"""A support chat thread between a customer and the admin."""
	STATUS_OPEN = 'open'
	STATUS_CLOSED = 'closed'
	STATUS_CHOICES = [
		(STATUS_OPEN, 'Open'),
		(STATUS_CLOSED, 'Closed'),
	]

	user = models.ForeignKey(
		'users.CustomUser', null=True, blank=True,
		on_delete=models.SET_NULL, related_name='chat_conversations'
	)
	guest_name = models.CharField(max_length=200, blank=True)
	guest_email = models.EmailField(blank=True)
	subject = models.CharField(max_length=200, blank=True, default='Support Request')
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
	# Session key used to identify guest users across page loads
	session_key = models.CharField(max_length=64, blank=True, db_index=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-updated_at']

	@property
	def display_name(self):
		if self.user:
			return self.user.get_full_name() or self.user.username
		return self.guest_name or 'Guest'

	@property
	def display_email(self):
		if self.user:
			return self.user.email
		return self.guest_email

	@property
	def unread_admin_count(self):
		"""Unread customer messages (from admin's perspective)."""
		return self.messages.filter(sender_type='customer', is_read=False).count()

	def __str__(self):
		return f"Chat #{self.pk} – {self.display_name}"


class ChatMessage(models.Model):
	"""A single message inside a ChatConversation."""
	SENDER_CUSTOMER = 'customer'
	SENDER_ADMIN = 'admin'
	SENDER_CHOICES = [
		(SENDER_CUSTOMER, 'Customer'),
		(SENDER_ADMIN, 'Admin'),
	]

	conversation = models.ForeignKey(
		ChatConversation, on_delete=models.CASCADE, related_name='messages'
	)
	sender_type = models.CharField(max_length=20, choices=SENDER_CHOICES)
	sender_name = models.CharField(max_length=200, blank=True)
	message = models.TextField()
	is_read = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['created_at']

	def __str__(self):
		return f"[{self.sender_type}] {self.message[:60]}"


class ChatAutoReply(models.Model):
	"""
	FAQ / auto-reply rule for the live chat bot.
	When a customer message contains any of the trigger keywords,
	the bot sends `response` automatically.
	"""
	CATEGORY_CHOICES = [
		('orders',   'Orders & Delivery'),
		('payment',  'Payment & Checkout'),
		('returns',  'Returns & Refunds'),
		('products', 'Products & Stock'),
		('account',  'Account & Login'),
		('general',  'General'),
	]

	category    = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='general')
	question    = models.CharField(max_length=300, help_text='Short label shown in admin (e.g. "Where is my order?")')
	keywords    = models.TextField(
		help_text='Comma-separated trigger words/phrases (e.g. track,where is my order,delivery status)'
	)
	response    = models.TextField(help_text='The message the bot will send back to the customer')
	priority    = models.PositiveSmallIntegerField(
		default=10,
		help_text='Higher number = checked first. Useful for overriding generic rules.'
	)
	is_active   = models.BooleanField(default=True)
	created_at  = models.DateTimeField(auto_now_add=True)
	updated_at  = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-priority', 'category', 'question']
		verbose_name = 'Chat Auto-Reply'
		verbose_name_plural = 'Chat Auto-Replies'

	def __str__(self):
		return f"[{self.get_category_display()}] {self.question}"

	def keyword_list(self):
		"""Return cleaned list of lowercase keyword strings."""
		return [k.strip().lower() for k in self.keywords.split(',') if k.strip()]
