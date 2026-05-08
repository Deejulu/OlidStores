# Generated manually for performance optimization
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_notification_action_url_notification_conversation_id_and_more'),
    ]

    operations = [
        # Add indexes to CustomUser model
        migrations.AddIndex(
            model_name='customuser',
            index=models.Index(fields=['email'], name='user_email_idx'),
        ),
        migrations.AddIndex(
            model_name='customuser',
            index=models.Index(fields=['role'], name='user_role_idx'),
        ),
        migrations.AddIndex(
            model_name='customuser',
            index=models.Index(fields=['email_verified'], name='user_email_verified_idx'),
        ),
        
        # Add indexes to Notification model
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['user', '-created_at'], name='notif_user_date_idx'),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['user', 'is_read'], name='notif_user_read_idx'),
        ),
        
        # Add indexes to Activity model
        migrations.AddIndex(
            model_name='activity',
            index=models.Index(fields=['user', '-timestamp'], name='activity_user_time_idx'),
        ),
        
        # Add indexes to OTPVerification model
        migrations.AddIndex(
            model_name='otpverification',
            index=models.Index(fields=['email', '-created_at'], name='otp_email_date_idx'),
        ),
        migrations.AddIndex(
            model_name='otpverification',
            index=models.Index(fields=['expires_at'], name='otp_expires_idx'),
        ),
    ]
