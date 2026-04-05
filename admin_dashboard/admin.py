
from django.contrib import admin
from .models import DailyMetric


@admin.register(DailyMetric)
class DailyMetricAdmin(admin.ModelAdmin):
    list_display = ('date', 'total_sales', 'order_count', 'completed_order_count', 'buyers')
    readonly_fields = ('created_at',)
    search_fields = ('date',)
