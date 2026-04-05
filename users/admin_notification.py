from django.contrib import admin
from .models_notification import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "created_at", "is_important", "is_read")
    list_filter = ("is_important", "is_read", "created_at")
    search_fields = ("title", "message", "user__username")
    actions = ["send_to_all"]

    def send_to_all(self, request, queryset):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.filter(is_active=True)
        count = 0
        for notification in queryset:
            for user in users:
                Notification.objects.create(
                    user=user,
                    title=notification.title,
                    message=notification.message,
                    is_important=notification.is_important
                )
                count += 1
        self.message_user(request, f"Sent {count} notifications to all users.")
    send_to_all.short_description = "Send selected notifications to all users"
