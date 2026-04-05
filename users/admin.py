from django.contrib import admin
from .models import Feedback

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
	list_display = ('user', 'created_at', 'is_resolved')
	list_filter = ('is_resolved', 'created_at')
	search_fields = ('user__username', 'message')
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.admin import AdminSite
## Removed custom admin site override to restore default permissions
from .models import CustomUser, Profile, Wishlist, Address
from products.models import Category, Product



class ProfileInline(admin.StackedInline):
	model = Profile
	can_delete = False
	verbose_name_plural = 'Profile'

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
	def get_fieldsets(self, request, obj=None):
		if not obj:
			return self.add_fieldsets
		return super().get_fieldsets(request, obj)

	def get_form(self, request, obj=None, **kwargs):
		form = super().get_form(request, obj, **kwargs)
		if obj:
			self.fieldsets = (
				(None, {'fields': ('username', 'email', 'password')}),
				('Personal info', {'fields': ('first_name', 'last_name', 'role')}),
				('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
				('Important dates', {'fields': ('last_login', 'date_joined')}),
			)
		return form
	list_display = (
		'username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff', 'is_superuser', 'date_joined', 'last_login'
	)
	search_fields = ('username', 'email', 'first_name', 'last_name', 'role')
	list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 'date_joined', 'last_login')
	inlines = [ProfileInline]
	fieldsets = (
		(None, {'fields': ('username', 'email', 'password')}),
		('Personal info', {'fields': ('first_name', 'last_name', 'role')}),
		('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
		('Important dates', {'fields': ('last_login', 'date_joined')}),
	)
	add_fieldsets = (
		(None, {
			'classes': ('wide',),
			'fields': ('username', 'email', 'role', 'password1', 'password2', 'is_active', 'is_staff', 'is_superuser'),
		}),
	)
	ordering = ('-date_joined',)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
	list_display = ('user', 'address', 'whatsapp')
	search_fields = ('user__email', 'address', 'whatsapp')

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
	list_display = ('user',)
	search_fields = ('user__email',)

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
	list_display = ('user', 'full_name', 'phone', 'address_line', 'is_default')
	search_fields = ('user__email', 'full_name', 'phone', 'address_line')

