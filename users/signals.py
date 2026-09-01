from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import CustomUser

User = get_user_model()


@receiver(pre_save, sender=CustomUser)
def ensure_account_id(sender, instance, **kwargs):
    if not instance.account_id:
        from .username_utils import generate_account_id
        account_id = generate_account_id(4)
        while CustomUser.objects.filter(account_id=account_id).exists():
            account_id = generate_account_id(4)
        instance.account_id = account_id
