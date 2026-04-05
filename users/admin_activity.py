from django.contrib import admin
from .models_activity import Activity

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("user", "activity_type", "product", "order_id", "timestamp")
    list_filter = ("activity_type", "timestamp")
    search_fields = ("user__username", "product__name", "order_id")
