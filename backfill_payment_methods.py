"""
Script to backfill payment_method field for existing PaymentTransaction records
from their raw_response JSON data.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_stores.settings')
django.setup()

from orders.models import PaymentTransaction

def backfill_payment_methods():
    """Extract payment method from raw_response and update payment_method field."""
    transactions = PaymentTransaction.objects.all()
    updated_count = 0
    skipped_count = 0
    
    print(f"Processing {transactions.count()} transactions...")
    
    for tx in transactions:
        # Skip if payment_method already set
        if tx.payment_method:
            skipped_count += 1
            continue
        
        # Try to extract from raw_response
        if tx.raw_response:
            payment_method = None
            
            # Try 'channel' field (most common)
            if 'channel' in tx.raw_response:
                payment_method = tx.raw_response['channel']
            
            # Try authorization.channel (alternative location)
            elif 'authorization' in tx.raw_response and isinstance(tx.raw_response['authorization'], dict):
                payment_method = tx.raw_response['authorization'].get('channel', '')
            
            # Update if found
            if payment_method:
                tx.payment_method = payment_method
                tx.save(update_fields=['payment_method'])
                updated_count += 1
                print(f"✓ Updated transaction {tx.reference}: {payment_method}")
            else:
                print(f"✗ No payment method found for {tx.reference}")
                skipped_count += 1
        else:
            print(f"✗ No raw_response for {tx.reference}")
            skipped_count += 1
    
    print(f"\nBackfill complete!")
    print(f"Updated: {updated_count}")
    print(f"Skipped: {skipped_count}")
    print(f"Total: {transactions.count()}")

if __name__ == '__main__':
    backfill_payment_methods()
