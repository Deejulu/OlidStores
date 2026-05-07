"""
Django management command to fix orders affected by delivery fee double-counting bug.

This command corrects orders where order.total incorrectly includes the delivery fee,
causing grand_total() to add the delivery fee twice.

Usage:
    python manage.py fix_delivery_fee_totals

On Render:
    python manage.py fix_delivery_fee_totals
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from orders.models import Order
from decimal import Decimal


class Command(BaseCommand):
    help = 'Fix orders where delivery fee was incorrectly included in order.total'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        self.stdout.write("=" * 70)
        self.stdout.write(self.style.SUCCESS("Delivery Fee Total Fix Tool"))
        self.stdout.write("=" * 70)
        self.stdout.write("")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))
            self.stdout.write("")
        
        # Get all orders with delivery fee
        orders = Order.objects.filter(delivery_fee__gt=0).order_by('id')
        
        self.stdout.write(f"Checking {orders.count()} orders with delivery fees...")
        self.stdout.write("")
        
        fixed_count = 0
        skipped_count = 0
        
        for order in orders:
            # Calculate actual products subtotal from order items
            try:
                products_subtotal = sum(item.subtotal() for item in order.items.all())
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Order #{order.id}: Error calculating subtotal - {e}")
                )
                skipped_count += 1
                continue
            
            # Check if order.total includes delivery fee (buggy data)
            # If order.total ≈ products + delivery, it's buggy
            expected_total_with_delivery = products_subtotal + order.delivery_fee
            
            # Allow small floating point differences (within 1 cent)
            if abs(order.total - expected_total_with_delivery) < Decimal('0.01'):
                # This order has the bug - order.total includes delivery
                old_total = order.total
                old_grand_total = order.grand_total()
                
                if not dry_run:
                    # Fix it: set order.total to products only
                    with transaction.atomic():
                        order.total = products_subtotal
                        order.save(update_fields=['total'])
                
                new_total = products_subtotal
                new_grand_total = new_total + order.delivery_fee
                
                self.stdout.write(f"Order #{order.id}:")
                self.stdout.write(f"  OLD: total=₦{old_total:,.2f}, delivery=₦{order.delivery_fee:,.2f}, grand_total=₦{old_grand_total:,.2f}")
                self.stdout.write(f"  NEW: total=₦{new_total:,.2f}, delivery=₦{order.delivery_fee:,.2f}, grand_total=₦{new_grand_total:,.2f}")
                
                if dry_run:
                    self.stdout.write(self.style.WARNING("  [Would fix in real run]"))
                else:
                    self.stdout.write(self.style.SUCCESS("  ✓ Fixed!"))
                
                self.stdout.write("")
                fixed_count += 1
            else:
                # Order is already correct
                skipped_count += 1
        
        self.stdout.write("=" * 70)
        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY RUN: Would fix {fixed_count} orders"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✓ Fixed {fixed_count} orders"))
        self.stdout.write(f"Skipped {skipped_count} orders (already correct)")
        self.stdout.write("=" * 70)
        
        if dry_run and fixed_count > 0:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("To apply these changes, run without --dry-run:"))
            self.stdout.write("  python manage.py fix_delivery_fee_totals")
