"""
Signals for core app - handles notifications for chat messages
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import ChatMessage
from users.models_notification import Notification

User = get_user_model()


@receiver(post_save, sender=ChatMessage)
def notify_chat_message(sender, instance, created, **kwargs):
    """
    Send notifications when chat messages are created:
    - Notify admin when customer sends a message
    - Notify customer when admin replies
    """
    if not created:
        return
    
    conversation = instance.conversation
    
    if instance.sender_type == 'customer':
        # Customer sent a message - notify all admin users
        admin_users = User.objects.filter(
            models.Q(role='admin') | models.Q(is_superuser=True),
            is_active=True
        ).distinct()
        
        for admin in admin_users:
            Notification.objects.create(
                user=admin,
                notification_type=Notification.TYPE_CHAT,
                title=f"New Chat Message from {conversation.display_name}",
                message=f"{instance.message[:100]}{'...' if len(instance.message) > 100 else ''}",
                conversation_id=conversation.id,
                action_url=f"/admin-dashboard/chat/{conversation.id}/",
                is_important=True
            )
    
    elif instance.sender_type == 'admin':
        # Admin replied - notify the customer
        if conversation.user:
            # Registered user
            Notification.objects.create(
                user=conversation.user,
                notification_type=Notification.TYPE_CHAT,
                title="Support Team Replied to Your Message",
                message=f"{instance.message[:100]}{'...' if len(instance.message) > 100 else ''}",
                conversation_id=conversation.id,
                action_url="/chat/",  # Customer chat page
                is_important=True
            )
        # Note: For guest users, we can't send notifications
        # They need to check the chat manually


# Import models here to avoid circular imports
from django.db import models
