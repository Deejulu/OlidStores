import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def verify_paystack_reference(reference):
    """Verify a Paystack transaction reference with Paystack API and return the parsed JSON or None on error."""
    if not reference:
        return None
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET}"}
    try:
        resp = requests.get(f"https://api.paystack.co/transaction/verify/{reference}", headers=headers, timeout=10)
        if resp.status_code != 200:
            logger.error("Paystack verify returned HTTP %s for reference %s: %s", resp.status_code, reference, resp.text[:500])
            return None
        return resp.json()
    except requests.exceptions.Timeout:
        logger.error("Paystack verify timed out for reference %s", reference)
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error("Paystack verify connection error for reference %s: %s", reference, e)
        return None
    except Exception as e:
        logger.exception("Paystack verify unexpected error for reference %s: %s", reference, e)
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
        
        # Find associated order: use the existing PaymentTransaction link only.
        # We never guess by amount+timestamp — that can silently pay the wrong order.
        order = None
        if existing and existing.order:
            order = existing.order
        else:
            # No existing transaction for this reference — transaction will be saved
            # without an order link and can be reconciled manually in the admin.
            logger.warning(
                'Paystack webhook: no order found for reference %s (amount=%.2f). '
                'PaymentTransaction saved without order link for manual reconciliation.',
                reference, amount_value
            )
        
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

                # Send branded confirmation email
                _send_order_confirmation_email(order)

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


def reverse_order_stock(order):
	"""
	Reverse stock for all items in an order.
	Used when orders are cancelled or deleted.
	
	Returns:
		dict: {
			'success': bool,
			'message': str,
			'reversed_items': [{'product_id': id, 'variant_id': id, 'quantity': qty}, ...]
		}
	"""
	from django.db import transaction
	from .models import OrderItem, OrderAuditLog
	from products.models import Product, ProductVariant
	
	try:
		with transaction.atomic():
			reversed_items = []
			
			# Get all items for this order
			items = order.items.all()
			
			for item in items:
				# Reverse product stock
				if item.product:
					product = Product.objects.select_for_update().get(id=item.product.id)
					product.stock += item.quantity
					product.save(update_fields=['stock', 'updated_at'])
					
					reversed_items.append({
						'product_id': item.product.id,
						'product_name': item.product.name,
						'quantity': item.quantity,
						'type': 'Product'
					})
				
				# Reverse variant stock if applicable
				if item.variant:
					variant = ProductVariant.objects.select_for_update().get(id=item.variant.id)
					variant.stock += item.quantity
					variant.save(update_fields=['stock', 'updated_at'])
					
					reversed_items.append({
						'variant_id': item.variant.id,
						'variant_name': str(item.variant),
						'quantity': item.quantity,
						'type': 'ProductVariant'
					})
			
			# Log the reversal in OrderAuditLog
			if reversed_items:
				OrderAuditLog.objects.create(
					order=order,
					action='stock_reversal',
					stock_reversed={
						'items': reversed_items,
						'total_items': len(items)
					}
				)
			
			return {
				'success': True,
				'message': f'Successfully reversed stock for {len(items)} items',
				'reversed_items': reversed_items
			}
			
	except Exception as e:
		logger.exception(f"Error reversing stock for order {order.id}: {str(e)}")
		return {
			'success': False,
			'message': f'Error reversing stock: {str(e)}',
			'reversed_items': []
		}


def _send_order_confirmation_email(order):
	"""Send branded HTML order confirmation email."""
	try:
		from django.core.mail import EmailMultiAlternatives
		from django.conf import settings
		from django.template.loader import render_to_string
		from django.http import HttpRequest

		if not order.email:
			return

		# Build a fake request for template context
		request = HttpRequest()
		request.META['HTTP_HOST'] = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost'

		context = {
			'order': order,
			'subject': f'Payment Confirmed - Order #{order.id}',
			'site_name': getattr(settings, 'SITE_NAME', 'Olid Stores'),
			'footer_text': '',
			'request': request,
		}

		html_content = render_to_string('emails/payment_confirmed.html', context)
		text_content = f"Your payment for Order #{order.id} has been confirmed. Your order is now being processed."

		msg = EmailMultiAlternatives(
			subject=f'Payment Confirmed - Order #{order.id}',
			body=text_content,
			from_email=settings.DEFAULT_FROM_EMAIL,
			to=[order.email],
		)
		msg.attach_alternative(html_content, "text/html")
		msg.send(fail_silently=True)
	except Exception:
		import logging
		logger = logging.getLogger(__name__)
		logger.exception(f"Failed to send order confirmation email for order {order.id}")


def send_order_shipped_email(order):
	"""Send branded HTML order shipped notification."""
	try:
		from django.core.mail import EmailMultiAlternatives
		from django.conf import settings
		from django.template.loader import render_to_string
		from django.http import HttpRequest

		if not order.email:
			return

		request = HttpRequest()
		request.META['HTTP_HOST'] = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost'

		context = {
			'order': order,
			'subject': f'Order Shipped - Order #{order.id}',
			'site_name': getattr(settings, 'SITE_NAME', 'Olid Stores'),
			'footer_text': '',
			'request': request,
		}

		html_content = render_to_string('emails/order_shipped.html', context)
		text_content = f"Your order #{order.id} has been shipped and is on its way!"

		msg = EmailMultiAlternatives(
			subject=f'Order Shipped - Order #{order.id}',
			body=text_content,
			from_email=settings.DEFAULT_FROM_EMAIL,
			to=[order.email],
		)
		msg.attach_alternative(html_content, "text/html")
		msg.send(fail_silently=True)
	except Exception:
		import logging
		logger = logging.getLogger(__name__)
		logger.exception(f"Failed to send order shipped email for order {order.id}")

