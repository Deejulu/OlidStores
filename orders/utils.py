import requests
from django.conf import settings


def verify_paystack_reference(reference):
    """Verify a Paystack transaction reference with Paystack API and return the parsed JSON or None on error."""
    if not reference:
        return None
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET}"}
    try:
        resp = requests.get(f"https://api.paystack.co/transaction/verify/{reference}", headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:
        return None


def process_paystack_webhook(payload):
    """Process a Paystack webhook payload dict.
    Returns (ok:bool, message:str)
    
    This function automatically:
    1. Creates/updates PaymentTransaction records
    2. Finds the associated Order (if exists) via metadata or creates one
    3. Updates order status to 'Processing' when payment succeeds
    """
    try:
        event = payload.get('event')
        data = payload.get('data', {})
        
        if event != 'charge.success':
            return (False, 'unsupported event')
        
        reference = data.get('reference')
        
        # idempotent: if a PaymentTransaction with this reference exists and has an order that's not pending, nothing to do
        from .models import PaymentTransaction, Order
        existing = PaymentTransaction.objects.filter(reference=reference).first()
        if existing and existing.order and existing.order.status != 'Pending':
            return (True, 'already processed')
        
        # verify via API for extra safety
        resp = verify_paystack_reference(reference)
        if not resp or not resp.get('status'):
            return (False, 'verify failed')
        
        txdata = resp.get('data', {})
        amount_kobo = int(txdata.get('amount', 0))
        amount_value = float(amount_kobo) / 100.0
        
        # Find associated order by reference (orders store paystack_reference in metadata)
        # Try to find order with matching payment reference
        order = None
        
        # First check if existing transaction has an order
        if existing and existing.order:
            order = existing.order
        else:
            # Try to find order that was created with this reference
            # Check for orders that might have been created during checkout
            # We'll match by close amount and timestamp (within last hour)
            from django.utils import timezone
            from datetime import timedelta
            from decimal import Decimal
            
            recent_threshold = timezone.now() - timedelta(hours=1)
            potential_orders = Order.objects.filter(
                created_at__gte=recent_threshold,
                status='Pending'
            )
            
            # Try to match by total amount (convert to match Paystack amount)
            for po in potential_orders:
                if abs(float(po.total) - amount_value) < 1.0:  # Allow small difference
                    order = po
                    break
        
        # Extract payment method from Paystack response
        payment_method = txdata.get('channel', '')
        if not payment_method and 'authorization' in txdata:
            payment_method = txdata['authorization'].get('channel', '')
        
        # Create or update PaymentTransaction
        if existing:
            existing.status = txdata.get('status', existing.status)
            existing.amount = amount_value
            existing.currency = txdata.get('currency', existing.currency)
            existing.payment_method = payment_method
            existing.raw_response = txdata
            if order:
                existing.order = order
            existing.save()
            pt = existing
        else:
            pt = PaymentTransaction.objects.create(
                reference=reference,
                order=order,
                amount=amount_value,
                currency=txdata.get('currency', 'NGN'),
                status=txdata.get('status', ''),
                payment_method=payment_method,
                raw_response=txdata
            )
        
        # AUTO-UPDATE ORDER STATUS when payment succeeds
        if order and txdata.get('status') == 'success':
            # Update order status to Processing (payment confirmed)
            if order.status == 'Pending':
                order.status = 'Processing'
                order.save()
                
                # Send confirmation email/notification if needed
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings
                    
                    if order.email:
                        send_mail(
                            f'Payment Confirmed - Order #{order.id}',
                            f'Your payment has been confirmed. Your order is now being processed.',
                            settings.DEFAULT_FROM_EMAIL,
                            [order.email],
                            fail_silently=True,
                        )
                except Exception:
                    pass  # Don't fail webhook if email fails
                
                return (True, f'payment confirmed, order #{order.id} updated to Processing')
            else:
                return (True, f'payment confirmed, order #{order.id} already {order.status}')
        elif order:
            return (True, f'transaction created/updated for order #{order.id}')
        else:
            return (True, 'transaction created without order link')
            
    except Exception as e:
        import traceback
        return (False, f'{str(e)}: {traceback.format_exc()}')

