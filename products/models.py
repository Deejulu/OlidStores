from django.db import models
from django.utils.text import slugify
from django.urls import reverse
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


def _compress_image_field(instance, field_name, max_size=(1200, 1200), quality=85):
    """
    Resize and compress an ImageField before it is saved to storage.
    Only processes new uploads (uncommitted files); existing DB records are skipped.
    Converts to JPEG to maximise compression. Transparent PNGs get a white background.
    """
    field = getattr(instance, field_name)
    # _committed is False only when a new file has been assigned but not yet saved
    if not field or getattr(field, '_committed', True):
        return
    try:
        from PIL import Image
        from io import BytesIO
        from django.core.files.uploadedfile import InMemoryUploadedFile

        img = Image.open(field)
        # Flatten transparency to white background
        if img.mode in ('RGBA', 'P', 'LA'):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                bg.paste(img, mask=img.split()[3])
            else:
                bg.paste(img.convert('RGBA'), mask=img.convert('RGBA').split()[3])
            img = bg
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        img.thumbnail(max_size, Image.LANCZOS)

        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        size = output.getbuffer().nbytes

        original_name = getattr(field, 'name', 'image')
        base_name = original_name.rsplit('.', 1)[0] if '.' in original_name else original_name
        new_name = f"{base_name}.jpg"

        setattr(instance, field_name, InMemoryUploadedFile(
            output, 'ImageField', new_name, 'image/jpeg', size, None
        ))
    except Exception:
        pass  # Never break a save due to compression failure


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_editable = models.BooleanField(default=True)
    is_sample = models.BooleanField(default=False, db_index=True, help_text='Marks categories created by the sample data tool')

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def can_edit(self, user):
        """Check if user has permission to edit this category"""
        return user.is_staff and self.is_editable

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_editable = models.BooleanField(default=True)
    is_sample = models.BooleanField(default=False, help_text='Marks products created by the sample data tool')
    stock = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=5, help_text='Alert when stock reaches this level')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at'], name='product_created_desc'),
            models.Index(fields=['category', '-created_at'], name='product_cat_created'),
            models.Index(fields=['stock'], name='product_stock'),
            models.Index(fields=['price'], name='product_price'),
            models.Index(fields=['-price'], name='product_price_desc'),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            qs = Product.objects.exclude(pk=self.pk) if self.pk else Product.objects.all()
            while qs.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        _compress_image_field(self, 'image', max_size=(1200, 1200))
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('products:product_detail', args=[self.slug])

    def is_in_stock(self):
        return self.stock > 0

    def low_stock_warning(self):
        if self.stock <= 5:
            return f"Low stock: Only {self.stock} left!"
        return ""

    def __str__(self):
        return self.name

    def can_edit(self, user):
        """Check if user has permission to edit this product"""
        return user.is_staff and self.is_editable

    def average_rating(self):
        """Calculate average rating from reviews"""
        reviews = self.reviews.all()
        if reviews.exists():
            return round(sum(r.rating for r in reviews) / reviews.count(), 1)
        return 0

    def review_count(self):
        """Get total number of reviews"""
        return self.reviews.count()

    def needs_restock(self):
        """Check if product needs restocking"""
        return self.stock <= self.reorder_level

    @property
    def primary_image(self):
        """Get the primary image for the product (main image or first additional image).
        
        Trusts that if an image field has a name, the file exists in storage.
        Avoids making HTTP calls to Supabase to verify existence on every render.
        """
        if self.image and getattr(self.image, 'name', None):
            return self.image

        # Use .all() to respect prefetch_related cache from product listing queries
        for pi in self.images.all():
            if pi.image and getattr(pi.image, 'name', None):
                return pi.image

        return None

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=100)
    additional_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    stock = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.product.name} - {self.name}"

from django.core.exceptions import ValidationError

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')

    class Meta:
        ordering = ['id']

    def clean(self):
        # Enforce maximum of 3 images per product
        if not self.pk:
            existing = ProductImage.objects.filter(product=self.product).count()
            if existing >= 3:
                raise ValidationError('A product may have up to 3 images.')

    def save(self, *args, **kwargs):
        self.clean()
        _compress_image_field(self, 'image', max_size=(1200, 1200))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Image for {self.product.name}"


class ProductReview(models.Model):
	"""Customer reviews and ratings for products"""
	product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
	title = models.CharField(max_length=200)
	review_text = models.TextField()
	verified_purchase = models.BooleanField(default=False)
	helpful_count = models.IntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']
		unique_together = ['product', 'user']  # One review per user per product
		indexes = [
			models.Index(fields=['product', '-created_at'], name='review_product_created'),
		]

	def __str__(self):
		return f"{self.user.username} - {self.product.name} ({self.rating}★)"


class ReviewHelpful(models.Model):
    """Track which users found reviews helpful"""
    review = models.ForeignKey(ProductReview, on_delete=models.CASCADE, related_name='helpful_votes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['review', 'user']

    def __str__(self):
        return f"{self.user.username} found review helpful"
