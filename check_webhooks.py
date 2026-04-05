"""
Script to check webhook events and their processing status
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_stores.settings')
django.setup()

from orders.models import WebhookEvent, PaymentTransaction, Order

def check_webhooks():
    """Check webhook events and their processing status."""
    print("=" * 70)
    print("WEBHOOK EVENTS ANALYSIS")
    print("=" * 70)
    
    # Count webhooks
    total_webhooks = WebhookEvent.objects.count()
    processed = WebhookEvent.objects.filter(processed=True).count()
    failed = total_webhooks - processed
    
    print(f"\n📊 SUMMARY:")
    print(f"   Total Webhooks Received: {total_webhooks}")
    print(f"   ✅ Successfully Processed: {processed}")
    print(f"   ❌ Failed/Unprocessed: {failed}")
    
    if total_webhooks == 0:
        print("\n⚠️  NO WEBHOOKS FOUND!")
        print("   This means Paystack is not sending webhooks to your server.")
        print("   Check your Paystack dashboard webhook settings.")
        return
    
    # Show recent webhooks
    print(f"\n📋 RECENT WEBHOOKS (Last 10):")
    print("-" * 70)
    
    recent = WebhookEvent.objects.order_by('-created_at')[:10]
    for wh in recent:
        status_icon = "✅" if wh.processed else "❌"
        print(f"\n{status_icon} Webhook #{wh.id}")
        print(f"   Event Type: {wh.event_type}")
        print(f"   Reference: {wh.reference}")
        print(f"   Created: {wh.created_at}")
        print(f"   Attempts: {wh.attempts}")
        print(f"   Processed: {wh.processed}")
        if wh.response_text:
            print(f"   Response: {wh.response_text}")
    
    # Check payment transactions
    print(f"\n💳 PAYMENT TRANSACTIONS:")
    print("-" * 70)
    
    transactions = PaymentTransaction.objects.order_by('-created_at')[:10]
    for tx in transactions:
        print(f"\n   Reference: {tx.reference}")
        print(f"   Status: {tx.status}")
        print(f"   Amount: ₦{tx.amount}")
        print(f"   Order ID: #{tx.order.id if tx.order else 'No order linked'}")
        if tx.order:
            print(f"   Order Status: {tx.order.status}")
            print(f"   Order Total: ₦{tx.order.total}")
    
    # Check order statuses
    print(f"\n📦 ORDER STATUS BREAKDOWN:")
    print("-" * 70)
    
    pending_orders = Order.objects.filter(status='Pending').count()
    processing_orders = Order.objects.filter(status='Processing').count()
    shipped_orders = Order.objects.filter(status='Shipped').count()
    delivered_orders = Order.objects.filter(status='Delivered').count()
    cancelled_orders = Order.objects.filter(status='Cancelled').count()
    
    print(f"   ⏳ Pending: {pending_orders}")
    print(f"   🔄 Processing: {processing_orders}")
    print(f"   📫 Shipped: {shipped_orders}")
    print(f"   ✅ Delivered: {delivered_orders}")
    print(f"   ❌ Cancelled: {cancelled_orders}")
    
    # Find unlinked successful payments
    print(f"\n⚠️  UNLINKED SUCCESSFUL PAYMENTS:")
    print("-" * 70)
    
    unlinked = PaymentTransaction.objects.filter(status='success', order__isnull=True)
    if unlinked.exists():
        print(f"   Found {unlinked.count()} successful payments without orders!")
        for tx in unlinked:
            print(f"   - {tx.reference}: ₦{tx.amount} on {tx.created_at}")
    else:
        print("   ✅ All successful payments are linked to orders")
    
    # Find pending orders with successful payments
    print(f"\n⚠️  PENDING ORDERS WITH SUCCESSFUL PAYMENTS:")
    print("-" * 70)
    
    pending_with_payment = Order.objects.filter(
        status='Pending',
        paymenttransaction__status='success'
    ).distinct()
    
    if pending_with_payment.exists():
        print(f"   Found {pending_with_payment.count()} pending orders that should be Processing!")
        for order in pending_with_payment:
            tx = order.paymenttransaction_set.filter(status='success').first()
            print(f"   - Order #{order.id}: ₦{order.total}")
            print(f"     Payment: {tx.reference} (₦{tx.amount})")
            print(f"     Created: {order.created_at}")
    else:
        print("   ✅ No pending orders with completed payments")
    
    print("\n" + "=" * 70)

if __name__ == '__main__':
    check_webhooks()
