from django.db import models
from django.conf import settings

class Notification(models.Model):
    """
    Notification system for both customers and admin users.
    Supports different notification types with links to related objects.
    """
    # Notification Types
    TYPE_GENERAL = 'general'
    TYPE_ORDER = 'order'
    TYPE_CHAT = 'chat'
    TYPE_PRODUCT = 'product'
    TYPE_PROMOTION = 'promotion'
    
    TYPE_CHOICES = [
        (TYPE_GENERAL, 'General'),
        (TYPE_ORDER, 'Order'),
        (TYPE_CHAT, 'Chat'),
        (TYPE_PRODUCT, 'Product'),
        (TYPE_PROMOTION, 'Promotion'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        help_text="Leave blank to send to all users"
    )
    notification_type = models.CharField(
        max_length=20, 
        choices=TYPE_CHOICES, 
        default=TYPE_GENERAL,
        db_index=True
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Related objects for context
    order_id = models.PositiveIntegerField(null=True, blank=True, help_text="Related order ID")
    conversation_id = models.PositiveIntegerField(null=True, blank=True, help_text="Related chat conversation ID")
    product_id = models.PositiveIntegerField(null=True, blank=True, help_text="Related product ID")
    
    # Action URL for quick navigation
    action_url = models.CharField(max_length=500, blank=True, help_text="URL to navigate when notification is clicked")
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    is_read = models.BooleanField(default=False, db_index=True)
    is_important = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        user_display = 'All' if self.user is None else self.user.username
        return f"{self.get_notification_type_display()}: {self.title} ({user_display})"
    
    def mark_as_read(self):
        """Mark this notification as read."""
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])
