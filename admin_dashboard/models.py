from django.db import models

try:
    # Django 3.1+ supports JSONField in core
    from django.db.models import JSONField
except Exception:
    # Fallback
    from django.contrib.postgres.fields import JSONField


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
        return f"DailyMetric {self.date} - ${self.total_sales}"

