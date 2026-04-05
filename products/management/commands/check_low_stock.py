from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from products.models import Product

User = get_user_model()

class Command(BaseCommand):
    help = 'Check for low stock products and send email alerts to admins'

    def add_arguments(self, parser):
        parser.add_argument(
            '--send-email',
            action='store_true',
            help='Actually send emails (default is to just print)',
        )

    def handle(self, *args, **options):
        send_email = options['send_email']
        
        # Find products that need restocking
        low_stock_products = Product.objects.filter(stock__lte=models.F('reorder_level'), stock__gt=0)
        out_of_stock_products = Product.objects.filter(stock=0)
        
        if not low_stock_products.exists() and not out_of_stock_products.exists():
            self.stdout.write(self.style.SUCCESS('✓ All products have sufficient stock'))
            return
        
        # Get admin emails
        admin_users = User.objects.filter(is_staff=True, is_active=True)
        admin_emails = [u.email for u in admin_users if u.email]
        
        if not admin_emails:
            self.stdout.write(self.style.WARNING('No admin emails found. Skipping email sending.'))
            return
        
        # Prepare email content
        subject = f'Low Stock Alert - {low_stock_products.count() + out_of_stock_products.count()} Products Need Attention'
        
        message_lines = ['Low Stock Alert Report\n', '=' * 50, '\n\n']
        
        if low_stock_products.exists():
            message_lines.append('LOW STOCK PRODUCTS:\n')
            message_lines.append('-' * 50 + '\n')
            for product in low_stock_products:
                message_lines.append(
                    f'• {product.name}\n'
                    f'  Category: {product.category.name}\n'
                    f'  Current Stock: {product.stock}\n'
                    f'  Reorder Level: {product.reorder_level}\n'
                    f'  Price: ₦{product.price}\n\n'
                )
        
        if out_of_stock_products.exists():
            message_lines.append('\nOUT OF STOCK PRODUCTS:\n')
            message_lines.append('-' * 50 + '\n')
            for product in out_of_stock_products:
                message_lines.append(
                    f'• {product.name}\n'
                    f'  Category: {product.category.name}\n'
                    f'  Reorder Level: {product.reorder_level}\n'
                    f'  Price: ₦{product.price}\n\n'
                )
        
        message_lines.append('\n' + '=' * 50 + '\n')
        message_lines.append(f'Total Products Needing Attention: {low_stock_products.count() + out_of_stock_products.count()}\n')
        message_lines.append('\nPlease restock these items as soon as possible.\n')
        
        message = ''.join(message_lines)
        
        # Print summary
        self.stdout.write(self.style.WARNING(f'\n⚠ Low Stock: {low_stock_products.count()} products'))
        self.stdout.write(self.style.ERROR(f'✗ Out of Stock: {out_of_stock_products.count()} products'))
        
        # Send email if flag is set
        if send_email:
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=admin_emails,
                    fail_silently=False,
                )
                self.stdout.write(self.style.SUCCESS(f'✓ Email sent to {len(admin_emails)} admin(s)'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Failed to send email: {str(e)}'))
        else:
            self.stdout.write(self.style.WARNING('\nℹ Email preview (use --send-email to actually send):'))
            self.stdout.write(self.style.WARNING(f'To: {", ".join(admin_emails)}'))
            self.stdout.write(self.style.WARNING(f'Subject: {subject}'))
            self.stdout.write('\n' + message)
