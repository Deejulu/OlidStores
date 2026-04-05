
from django.contrib import admin
from .models import GalleryImage, SiteContent

@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ('title', 'image')
    search_fields = ('title',)


from .forms import SiteContentForm, BannerImageForm
from .models import BannerImage, HeroImage, ContactMessage, TeamMember

@admin.register(BannerImage)
class BannerImageAdmin(admin.ModelAdmin):
    list_display = ('title', 'thumbnail_preview', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('title',)

    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return f"<img src='{obj.thumbnail.url}' style='height:40px;'/>"
        if obj.image:
            return f"<img src='{obj.image.url}' style='height:40px;'/>"
        return ''
    thumbnail_preview.allow_tags = True
    thumbnail_preview.short_description = 'Preview'

@admin.register(HeroImage)
class HeroImageAdmin(admin.ModelAdmin):
    list_display = ('title', 'thumbnail_preview', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('title',)

    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return f"<img src='{obj.thumbnail.url}' style='height:40px;'/>"
        if obj.image:
            return f"<img src='{obj.image.url}' style='height:40px;'/>"
        return ''
    thumbnail_preview.allow_tags = True
    thumbnail_preview.short_description = 'Preview'

@admin.register(SiteContent)
class SiteContentAdmin(admin.ModelAdmin):
    form = SiteContentForm
    list_display = ('key', 'title', 'phone', 'email', 'updated_at')
    search_fields = ('key', 'title', 'phone', 'email')
    readonly_fields = ('updated_at',)

    def get_fieldsets(self, request, obj=None):
        # Dynamic fieldsets for clarity
        base = [
            (None, {'fields': ('key', 'title', 'content')})
        ]
        if obj and obj.key == 'contact':
            base.append(('Contact Info', {
                'fields': ('phone', 'email', 'social_links', 'twitter', 'instagram', 'facebook', 'whatsapp', 'map_embed'),
                'description': 'Edit the contact information and map for the Contact page. Use the platform fields to enter handles or full URLs; handles like @yourhandle or just yourhandle are supported and will be converted to profile URLs.',
            }))
        base.append(('Other', {'fields': ('updated_at',)}))
        return base


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at', 'ip_address', 'user')
    actions = ['mark_read']

    def mark_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_read.short_description = 'Mark selected messages as read'


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'title', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('name', 'title')

