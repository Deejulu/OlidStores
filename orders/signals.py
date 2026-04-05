from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order
from users.models_notification import Notification

@receiver(post_save, sender=Order)
def notify_new_order(sender, instance, created, **kwargs):
    if created and instance.user:
        Notification.objects.create(
            user=instance.user,
            title="Order Placed!",
            message=f"Your order #{instance.id} has been placed successfully.",
            is_important=True
        )
