from django.db import models
from django.conf import settings

try:
    # Django 3.1+ supports JSONField in core
    from django.db.models import JSONField
except Exception:
    # Fallback
    from django.contrib.postgres.fields import JSONField


class AdminAuditLog(models.Model):
    """Records every admin action on orders, products, and content so there is always a trail of who changed what."""
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_CREATE = 'create'
    ACTION_CHOICES = [
        (ACTION_UPDATE, 'Update'),
        (ACTION_DELETE, 'Delete'),
        (ACTION_CREATE, 'Create'),
    ]

    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, default=ACTION_UPDATE)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=50, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    changes = JSONField(null=True, blank=True, help_text='Dict of field: [old_value, new_value] for each changed field')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp'], name='auditlog_timestamp'),
            models.Index(fields=['model_name', 'object_id'], name='auditlog_object'),
        ]

    def __str__(self):
        return f"{self.admin_user} {self.action} {self.model_name} #{self.object_id} at {self.timestamp:%Y-%m-%d %H:%M}"


class DailyMetric(models.Model):
    date = models.DateField(unique=True)
    total_sales = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    order_count = models.IntegerField(default=0)
    completed_order_count = models.IntegerField(default=0)
    total_items = models.IntegerField(default=0)
    buyers = models.IntegerField(default=0)
    # precompute category revenue and top products as JSON to avoid heavy joins on read
    revenue_by_category = JSONField(blank=True, null=True, default=dict)
    top_products = JSONField(blank=True, null=True, default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"DailyMetric {self.date} - ₦{self.total_sales}"

