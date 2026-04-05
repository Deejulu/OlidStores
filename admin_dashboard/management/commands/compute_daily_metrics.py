from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from products.models import Product, Category
from orders.models import Order, OrderItem
from admin_dashboard.models import DailyMetric


class Command(BaseCommand):
    help = 'Compute daily metrics (rollups) for the given date range or last N days'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=90, help='Number of past days to compute (default 90)')
        parser.add_argument('--start', type=str, help='Start date YYYY-MM-DD')
        parser.add_argument('--end', type=str, help='End date YYYY-MM-DD')

    def handle(self, *args, **options):
        days = options['days']
        start = options.get('start')
        end = options.get('end')
        today = timezone.now().date()
        if start and end:
            start_date = datetime.strptime(start, '%Y-%m-%d').date()
            end_date = datetime.strptime(end, '%Y-%m-%d').date()
        else:
            end_date = today
            start_date = today - timedelta(days=days-1)

        self.stdout.write(f"Computing daily metrics from {start_date} to {end_date}")

        revenue_expr = ExpressionWrapper(F('orderitem__quantity') * F('orderitem__price'), output_field=DecimalField())

        d = start_date
        while d <= end_date:
            day_start = timezone.make_aware(datetime.combine(d, datetime.min.time())) if hasattr(timezone, 'make_aware') else datetime.combine(d, datetime.min.time())
            day_end = timezone.make_aware(datetime.combine(d, datetime.max.time())) if hasattr(timezone, 'make_aware') else datetime.combine(d, datetime.max.time())

            orders_qs = Order.objects.filter(created_at__range=(day_start, day_end))
            completed_qs = orders_qs.filter(status__in=['Processing', 'Completed'])

            total_sales = completed_qs.aggregate(total=Sum('total'))['total'] or 0
            order_count = orders_qs.count()
            completed_order_count = completed_qs.count()
            total_items = OrderItem.objects.filter(order__in=completed_qs).aggregate(total_qty=Sum('quantity'))['total_qty'] or 0
            buyers = completed_qs.values('user').distinct().count()

            # revenue by category
            cat_expr = ExpressionWrapper(F('products__orderitem__quantity') * F('products__orderitem__price'), output_field=DecimalField())
            categories = Category.objects.filter(products__orderitem__order__in=completed_qs).distinct().annotate(revenue=Sum(cat_expr)).order_by('-revenue')
            revenue_by_category = {c.name: float(getattr(c, 'revenue') or 0) for c in categories}

            # top products
            top_products_qs = Product.objects.filter(orderitem__order__in=completed_qs).annotate(revenue=Sum(revenue_expr), total_qty=Sum('orderitem__quantity')).order_by('-revenue')[:10]
            top_products = [{'id': p.id, 'name': p.name, 'revenue': float(getattr(p, 'revenue') or 0), 'qty': int(getattr(p, 'total_qty') or 0)} for p in top_products_qs]

            dm, created = DailyMetric.objects.update_or_create(
                date=d,
                defaults={
                    'total_sales': total_sales,
                    'order_count': order_count,
                    'completed_order_count': completed_order_count,
                    'total_items': total_items,
                    'buyers': buyers,
                    'revenue_by_category': revenue_by_category,
                    'top_products': top_products,
                }
            )
            self.stdout.write(f"Saved {dm} (created={created})")
            d = d + timedelta(days=1)

        self.stdout.write(self.style.SUCCESS('Daily metrics computed.'))