# Generated manually for performance optimization
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0014_order_deleted_at_order_is_deleted_orderauditlog'),
    ]

    operations = [
        # Add additional indexes to Order model for faster queries
        # Note: Some indexes already exist from previous migrations (order_user_created, order_status, order_created_desc)
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['is_deleted', '-created_at'], name='order_deleted_date_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['payment_method'], name='order_payment_method_idx'),
        ),
        
        # Add indexes to Cart model
        migrations.AddIndex(
            model_name='cart',
            index=models.Index(fields=['user'], name='cart_user_idx'),
        ),
        migrations.AddIndex(
            model_name='cart',
            index=models.Index(fields=['session_key'], name='cart_session_idx'),
        ),
        
        # Add indexes to CartItem model
        migrations.AddIndex(
            model_name='cartitem',
            index=models.Index(fields=['cart'], name='cartitem_cart_idx'),
        ),
        
        # Add indexes to PaymentTransaction model
        migrations.AddIndex(
            model_name='paymenttransaction',
            index=models.Index(fields=['reference'], name='payment_ref_idx'),
        ),
        migrations.AddIndex(
            model_name='paymenttransaction',
            index=models.Index(fields=['order', '-created_at'], name='payment_order_date_idx'),
        ),
    ]
