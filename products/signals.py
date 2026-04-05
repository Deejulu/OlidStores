from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Product
from users.models_notification import Notification
from django.contrib.auth import get_user_model

@receiver(post_save, sender=Product)
def notify_new_product(sender, instance, created, **kwargs):
    if created:
        User = get_user_model()
        users = User.objects.filter(is_active=True)
        for user in users:
            Notification.objects.create(
                user=user,
                title="New Product Added!",
                message=f"Check out our new product: {instance.name}",
                is_important=True
            )
