from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from products.models import Product
from orders.models import Order
import io, csv

class Command(BaseCommand):
    help = 'Send analytics report for the last 30 days to ADMINS'

    def handle(self, *args, **options):
        end_dt = timezone.now()
        start_dt = end_dt - timedelta(days=29)
        orders_qs = Order.objects.filter(created_at__range=(start_dt, end_dt))
        completed_orders_qs = orders_qs.filter(status__in=['Processing', 'Completed'])
        total_sales = completed_orders_qs.aggregate(total=Sum('total'))['total'] or 0
        order_count = orders_qs.count()
        completed_order_count = completed_orders_qs.count()

        body = f"Analytics report for {start_dt.date()} to {end_dt.date()}\n\n"
        body += f"Total sales: ${float(total_sales):.2f}\nOrders: {order_count} (Completed: {completed_order_count})\n"

        revenue_expr = ExpressionWrapper(F('orderitem__quantity') * F('orderitem__price'), output_field=DecimalField())
        top_products_revenue_local = (
            Product.objects.filter(orderitem__order__in=completed_orders_qs)
            .annotate(revenue=Sum(revenue_expr))
            .order_by('-revenue')[:20]
        )

        top_products_csv = io.StringIO()
        writer = csv.writer(top_products_csv)
        writer.writerow(['Product ID', 'Name', 'Qty Sold', 'Revenue'])
        for p in top_products_revenue_local:
            writer.writerow([p.id, p.name, getattr(p, 'total_qty', 0), getattr(p, 'revenue', 0)])
        top_products_csv.seek(0)

        orders_csv = io.StringIO()
        writer = csv.writer(orders_csv)
        writer.writerow(['Order ID', 'User', 'Status', 'Total', 'Created At'])
        for o in orders_qs.order_by('-created_at'):
            writer.writerow([o.id, o.user.username if o.user else 'Guest', o.status, float(o.total), o.created_at])
        orders_csv.seek(0)

        recipients = [email for name, email in getattr(settings, 'ADMINS', [])]
        if not recipients:
            self.stdout.write('No ADMINS configured. Exiting.')
            return
        email = EmailMessage(subject=f"Analytics Report {start_dt.date()} - {end_dt.date()}", body=body, to=recipients)
        email.attach(f'top_products_{start_dt.date()}_{end_dt.date()}.csv', top_products_csv.getvalue(), 'text/csv')
        email.attach(f'orders_{start_dt.date()}_{end_dt.date()}.csv', orders_csv.getvalue(), 'text/csv')
        email.send(fail_silently=False)
        self.stdout.write(self.style.SUCCESS('Analytics report sent to ADMINS'))