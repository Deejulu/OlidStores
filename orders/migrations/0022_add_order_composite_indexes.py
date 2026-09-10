from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0021_alter_cart_session_key_cart_cart_user_idx_and_more'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['is_deleted', 'status'], name='order_deleted_status'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['is_deleted', 'status', '-created_at'], name='order_deleted_status_created'),
        ),
    ]
