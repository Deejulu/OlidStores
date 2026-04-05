

from django.contrib import admin
from .models import Product, Category, ProductVariant, ProductImage, ProductReview, ReviewHelpful


class ProductImageInline(admin.TabularInline):
	model = ProductImage
	extra = 3
	max_num = 3
	min_num = 0
	verbose_name = 'Product Image'
	verbose_name_plural = 'Product Images'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
	list_display = ('name', 'category', 'price', 'stock', 'created_at')
	prepopulated_fields = {"slug": ("name",)}
	search_fields = ('name', 'category__name')
	list_filter = ('category', 'created_at')
	inlines = [ProductImageInline]


def populate_sample_action(modeladmin, request, queryset):
	from django.core.management import call_command
	call_command('populate_sample')
	modeladmin.message_user(request, "Sample categories and products have been created.")
populate_sample_action.short_description = "Populate sample categories and products"

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
	list_display = ('name', 'description')
	prepopulated_fields = {"slug": ("name",)}
	search_fields = ('name',)
	actions = [populate_sample_action]

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
	list_display = ('product', 'name', 'additional_price', 'stock')
	search_fields = ('product__name', 'name')

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
	list_display = ('product', 'image')
	search_fields = ('product__name',)


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
	list_display = ('product', 'user', 'rating', 'verified_purchase', 'helpful_count', 'created_at')
	list_filter = ('rating', 'verified_purchase', 'created_at')
	search_fields = ('product__name', 'user__username', 'title', 'review_text')
	readonly_fields = ('helpful_count', 'created_at', 'updated_at')
	actions = ['mark_verified_purchase']

	def mark_verified_purchase(self, request, queryset):
		updated = queryset.update(verified_purchase=True)
		self.message_user(request, f'{updated} reviews marked as verified purchases.')
	mark_verified_purchase.short_description = 'Mark as verified purchase'


@admin.register(ReviewHelpful)
class ReviewHelpfulAdmin(admin.ModelAdmin):
	list_display = ('review', 'user', 'created_at')
	search_fields = ('review__product__name', 'user__username')
