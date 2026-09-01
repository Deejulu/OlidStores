import hmac
import hashlib
import json
import requests
import logging
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)
from .models import Order, OrderItem, PaymentTransaction, CheckoutSettings, PaymentSettings

from .utils import verify_paystack_reference as _verify_paystack_reference
# Replaced inline verifier with shared utils.verify_paystack_reference
# _verify_paystack_reference now returns the full JSON or None on error.

from django.contrib.auth.decorators import login_required

def checkout_view(request):
	# ...existing code...
	cart = None
	items = []
	total = 0
	# load admin-configured fees (fallback to settings or CheckoutSettings) - cached for 5 minutes
	from django.core.cache import cache
	cs = cache.get('checkout_settings')
	if cs is None:
		cs = CheckoutSettings.objects.first()
		cache.set('checkout_settings', cs, 300)
	delivery_fee_24h = cs.delivery_fee_24h if cs else getattr(settings, 'DELIVERY_FEE_24H', 0)
	delivery_fee_2d = cs.delivery_fee_2d if cs else getattr(settings, 'DELIVERY_FEE_2D', 0)

	# load admin-managed payment options - cached for 5 minutes
	payment_settings = cache.get('payment_settings')
	if payment_settings is None:
		payment_settings = PaymentSettings.objects.first()
		cache.set('payment_settings', payment_settings, 300)
	enable_paystack = bool(settings.PAYSTACK_PUBLIC) and (payment_settings.enable_paystack if payment_settings else True)
	pay_on_delivery_max = payment_settings.pay_on_delivery_max if payment_settings else 100000.00
	enable_manual = False
	enable_pay_on_delivery = False
	# Prefer SiteContent values if present (Manage Site Content integration)
	try:
		from core.models import SiteContent
		_sc = SiteContent.objects.filter(key='checkout').first()
		if _sc:
			# Only override if SiteContent explicitly sets a non-zero value
			if _sc.delivery_fee_24h is not None and float(_sc.delivery_fee_24h) != 0.0:
				delivery_fee_24h = _sc.delivery_fee_24h
			if _sc.delivery_fee_2d is not None and float(_sc.delivery_fee_2d) != 0.0:
				delivery_fee_2d = _sc.delivery_fee_2d
	except Exception:
		pass
	if request.user.is_authenticated:
		cart = Cart.objects.filter(user=request.user).first()
	else:
		session_key = request.session.session_key
		if not session_key:
			request.session.create()
			session_key = request.session.session_key
		cart = Cart.objects.filter(session_key=session_key, user=None).first()

	# Load items once with select_related to avoid N+1 queries
	if cart:
		items = list(cart.items.select_related('product', 'variant').all())

	# Block access if any cart item exceeds available stock or is critically low
	for item in items:
		if item.variant:
			# Check if stock is critically low
			if item.variant.stock <= 1:
				messages.error(request, f"'{item.variant.name}' is critically low in stock and cannot be ordered.")
				return redirect('orders:cart')
			if item.variant.stock < item.quantity:
				messages.error(request, f"Insufficient stock for {item.variant.name}. Please adjust your cart.")
				return redirect('orders:cart')
		else:
			# Check if stock is critically low
			if item.product.stock <= 1:
				messages.error(request, f"'{item.product.name}' is critically low in stock and cannot be ordered.")
				return redirect('orders:cart')
			if item.product.stock < item.quantity:
				messages.error(request, f"Insufficient stock for {item.product.name}. Please adjust your cart.")
				return redirect('orders:cart')
	
	# Validate cart prices (warn if prices have changed since item was added)
	price_changes = []
	for item in items:
		current_price = float(item.product.price)
		cart_price = float(item.price)
		if current_price != cart_price:
			price_changes.append({
				'product': item.product.name,
				'old_price': cart_price,
				'new_price': current_price,
				'difference': current_price - cart_price
			})
	
	# Display price change warnings (but allow checkout to proceed)
	for change in price_changes:
		if change['difference'] > 0:
			messages.warning(
				request,
				f"{change['product']} price increased from ₦{change['old_price']:.2f} to ₦{change['new_price']:.2f} (difference: +₦{change['difference']:.2f})"
			)
		else:
			messages.info(
				request,
				f"{change['product']} price decreased from ₦{change['old_price']:.2f} to ₦{change['new_price']:.2f} (difference: -₦{abs(change['difference']):.2f})"
			)
	
	if request.method == 'POST':
		payment_method = request.POST.get('payment_method')
		full_name = request.POST.get('full_name')
		phone = request.POST.get('phone')
		email = request.POST.get('email')
		delivery_address = request.POST.get('delivery_address')
		notes = request.POST.get('notes')
		notes = notes or ''
		paystack_reference = request.POST.get('paystack_reference')
		receipt_file = request.FILES.get('receipt')
		
		if payment_method in ('manual', 'pay_on_delivery'):
			messages.error(request, 'This payment method is no longer available. Please use Paystack.')
			return redirect('orders:checkout')
		
		# Validate receipt file size (5MB limit)
		if receipt_file and receipt_file.size > 5 * 1024 * 1024:
			messages.error(request, 'Receipt file too large. Maximum size is 5MB.')
			return redirect('orders:checkout')
		
		delivery_option = request.POST.get('delivery_option')
		delivery_fee = 0
		if delivery_option == '24h':
			delivery_fee = delivery_fee_24h
		elif delivery_option == '2d':
			delivery_fee = delivery_fee_2d

		if cart:
			items = cart.items.select_related('product', 'variant').all()
			base_total = sum(item.subtotal() for item in items)
			total = base_total  # Store ONLY products subtotal, not delivery fee

		if payment_method == 'manual':
			if not enable_manual:
				messages.error(request, 'Manual bank transfer is not available right now.')
				return redirect('orders:checkout')
			# Manual payment: check stock availability (do NOT reduce yet)
			# Stock will be reduced when admin confirms payment (status -> 'Processing')
			from django.db import transaction
			with transaction.atomic():
				for item in items:
					if item.variant:
						pv = ProductVariant.objects.select_for_update().get(id=item.variant.id)
						if pv.stock < item.quantity:
							messages.error(request, f'Insufficient stock for {pv.name}.')
							return redirect('orders:checkout')
					else:
						p = Product.objects.select_for_update().get(id=item.product.id)
						if p.stock < item.quantity:
							messages.error(request, f'Insufficient stock for {p.name}.')
							return redirect('orders:checkout')
				order = Order.objects.create(
					user=request.user if request.user.is_authenticated else None,
					full_name=full_name,
					phone=phone,
					email=email,
					delivery_address=delivery_address,
					total=total,
					delivery_fee=delivery_fee,
					delivery_option=delivery_option or '2d',
					status='Pending',
					notes=notes or '',
					receipt=receipt_file,
					payment_method='manual'
				)
				for item in items:
					OrderItem.objects.create(
						order=order,
						product=item.product,
						variant=item.variant,
						quantity=item.quantity,
						price=item.price
					)
			# Track order placement activity
			user = request.user
			if user.is_authenticated:
				try:
					from users.models_activity import Activity
					Activity.objects.create(user=user, activity_type='order', order_id=order.id)
				except Exception:
					pass
			cart.items.all().delete()
			messages.success(request, 'Manual payment submitted. Your order will be confirmed within 24 hours.')
			return redirect('orders:order_confirmation', order_id=order.id, token=order.confirmation_token)
		elif payment_method == 'pay_on_delivery':
			logger.warning(f"Pay on Delivery selected. enable={enable_pay_on_delivery}, total={total}, delivery_fee={delivery_fee}, max={pay_on_delivery_max}")
			if not enable_pay_on_delivery:
				messages.error(request, 'Pay on Delivery is not enabled.')
				return redirect('orders:checkout')
			# Check if order total (products + delivery) exceeds pay-on-delivery limit
			grand_total = total + (delivery_fee or Decimal('0.00'))
			logger.warning(f"Grand total: {grand_total}, max: {pay_on_delivery_max}, items count: {items.count() if items else 0}")
			if grand_total > pay_on_delivery_max:
				messages.error(request, f'Pay on Delivery is only available for orders up to ₦{pay_on_delivery_max:.2f}.')
				return redirect('orders:checkout')
			# Reserve stock and create the order as pending
			from django.db import transaction
			try:
				with transaction.atomic():
					for item in items:
						logger.warning(f"Processing item: {item.product.name}, qty={item.quantity}")
						if item.variant:
							pv = ProductVariant.objects.select_for_update().get(id=item.variant.id)
							if pv.stock < item.quantity:
								messages.error(request, f'Insufficient stock for {pv.name}.')
								return redirect('orders:checkout')
							pv.stock -= item.quantity
							pv.save()
						else:
							p = Product.objects.select_for_update().get(id=item.product.id)
							if p.stock < item.quantity:
								messages.error(request, f'Insufficient stock for {p.name}.')
								return redirect('orders:checkout')
							p.stock -= item.quantity
							p.save()
					order = Order.objects.create(
						user=request.user if request.user.is_authenticated else None,
						full_name=full_name,
						phone=phone,
						email=email,
						delivery_address=delivery_address,
						total=total,
						delivery_fee=delivery_fee,
						delivery_option=delivery_option or '2d',
						status='Pending',
						notes=notes,
						payment_method='pay_on_delivery'
					)
					logger.warning(f"Order created: {order.id}")
					for item in items:
						OrderItem.objects.create(
							order=order,
							product=item.product,
							variant=item.variant,
							quantity=item.quantity,
							price=item.price
						)
			except Exception as e:
				logger.error(f"Error creating order: {e}")
				messages.error(request, f'Error creating order: {e}')
				return redirect('orders:checkout')
			# Track order placement activity
			user = request.user
			if user.is_authenticated:
				try:
					from users.models_activity import Activity
					Activity.objects.create(user=user, activity_type='order', order_id=order.id)
				except Exception:
					pass
			cart.items.all().delete()
			messages.success(request, 'Pay on Delivery order submitted. Our team will contact you shortly.')
			return redirect('orders:order_confirmation', order_id=order.id, token=order.confirmation_token)
		elif payment_method == 'paystack' and paystack_reference:
			# Final backend stock check before payment
			for item in items:
				if item.variant:
					if item.variant.stock < item.quantity:
						messages.error(request, f'Insufficient stock for {item.variant.name}. Please adjust your cart.')
						return redirect('orders:checkout')
				else:
					if item.product.stock < item.quantity:
						messages.error(request, f'Insufficient stock for {item.product.name}. Please adjust your cart.')
						return redirect('orders:checkout')
			# Verify with Paystack
			resp = _verify_paystack_reference(paystack_reference)
			if not resp or not resp.get('status'):
				messages.error(request, 'Payment verification failed. Please contact support.')
				return redirect('orders:checkout')
			data = resp.get('data', {})
			# Check transaction status and amount
			if data.get('status') == 'success':
				# Reject non-NGN transactions (e.g. USD multi-currency)
				tx_currency = (data.get('currency') or 'NGN').upper()
				if tx_currency != 'NGN':
					messages.error(request, f'This store only accepts Nigerian Naira (₦). Your payment was charged in {tx_currency}. Please contact support for a refund.')
					return redirect('orders:checkout')
				# Verify payment amount matches expected total (products + delivery)
				amount_kobo = int(data.get('amount', 0))
				expected_total = total + (delivery_fee or Decimal('0.00'))
				expected_kobo = int(round(float(expected_total) * 100))
				if amount_kobo != expected_kobo:
					messages.error(request, 'Payment amount mismatch. Please contact support.')
					return redirect('checkout')
				# Idempotency: skip if transaction already processed
				existing = PaymentTransaction.objects.filter(reference=paystack_reference).first()
				if existing and existing.order:
					messages.success(request, 'Payment already processed. Thank you!')
					return redirect('orders:cart')
				# Reserve stock (atomic lock) before creating order
				from django.db import transaction
				with transaction.atomic():
					for item in items:
						if item.variant:
							pv = ProductVariant.objects.select_for_update().get(id=item.variant.id)
							pv.stock -= item.quantity
							pv.save()
						else:
							p = Product.objects.select_for_update().get(id=item.product.id)
							p.stock -= item.quantity
							p.save()
					# Create order and items
					order = Order.objects.create(
						user=request.user if request.user.is_authenticated else None,
						full_name=full_name,
						phone=phone,
						email=email,
						delivery_address=delivery_address,
						total=total,
						delivery_fee=delivery_fee,
						delivery_option=delivery_option or '2d',
						status='Processing',
						notes=notes,
						payment_method='paystack'
					)
					for item in items:
						OrderItem.objects.create(
							order=order,
							product=item.product,
							variant=item.variant,
							quantity=item.quantity,
							price=item.price
						)
					# record transaction
					payment_channel = data.get('channel') or (data.get('authorization') or {}).get('channel') or ''
					pt = PaymentTransaction.objects.create(
						reference=paystack_reference,
						order=order,
						amount=float(data.get('amount', 0)) / 100.0,
						currency=data.get('currency', 'NGN'),
						status=data.get('status', ''),
						payment_method=payment_channel,
						raw_response=data
					)
				cart.items.all().delete()
				# Track activity
				user = request.user
				if user.is_authenticated:
					try:
						from users.models_activity import Activity
						Activity.objects.create(user=user, activity_type='order', order_id=order.id)
					except Exception:
						pass
			messages.success(request, 'Payment verified and order created. Thank you!')
			return redirect('orders:order_confirmation', order_id=order.id, token=order.confirmation_token)
		else:
			# Payment verification failed
			messages.error(request, 'Payment was not successful. Please try again or contact support.')
			return redirect('orders:checkout')
	# Invalid payment method (only check on POST)
	if request.method == 'POST' and payment_method not in ('manual', 'pay_on_delivery', 'paystack'):
		messages.error(request, 'Invalid payment method or missing information.')
	
	bank_name = 'GTBank'
	account_name = 'OD Ltd'
	account_number = '0123456789'
	
	if cart and not items:
		items = list(cart.items.select_related('product', 'variant').all())
	if cart:
		total = sum(item.subtotal() for item in items)
		
		# Get bank transfer details from SiteContent
		try:
			from core.models import SiteContent
			_sc = SiteContent.objects.filter(key='checkout').first()
			if _sc:
				if _sc.bank_name:
					bank_name = _sc.bank_name
				if _sc.account_name:
					account_name = _sc.account_name
				if _sc.account_number:
					account_number = _sc.account_number
		except Exception:
			pass
		
	context = {
	'cart': cart,
	'items': items,
	'base_total': total,
	'total': total,  # may be adjusted on the client when delivery is selected
	'PAYSTACK_PUBLIC': settings.PAYSTACK_PUBLIC,
	'enable_paystack': enable_paystack,
	'enable_manual': enable_manual,
	'enable_pay_on_delivery': enable_pay_on_delivery,
	'pay_on_delivery_max': pay_on_delivery_max,
	'delivery_fee_24h': delivery_fee_24h,
	'delivery_fee_2d': delivery_fee_2d,
	'selected_delivery_option': '2d',
	'bank_name': bank_name,
	'account_name': account_name,
	'account_number': account_number,
	}
	return render(request, 'orders/checkout.html', context)


@csrf_exempt
def paystack_webhook(request):
	# Validate signature
	sig = request.headers.get('x-paystack-signature', '')
	body = request.body
	computed = hmac.new(settings.PAYSTACK_SECRET.encode(), body, hashlib.sha512).hexdigest()
	if not hmac.compare_digest(computed, sig):
		return HttpResponse(status=400)
	payload = json.loads(body)
	event = payload.get('event')
	data = payload.get('data', {})
	# persist webhook for reliable processing and observability
	from .models import WebhookEvent
	ev = WebhookEvent.objects.create(
		provider='paystack',
		event_type=event or '',
		reference=data.get('reference'),
		payload=payload,
		headers={k: v for k, v in request.headers.items()},
	)
	# Process synchronously (safe) but allow reprocessing via management command when needed
	from .utils import process_paystack_webhook
	ok, msg = process_paystack_webhook(payload)
	ev.attempts = ev.attempts + 1
	ev.last_attempt = timezone.now()
	ev.response_text = msg or ''
	if ok:
		ev.processed = True
		ev.processed_at = timezone.now()
	ev.save()
	return HttpResponse(status=200)

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from products.models import Product, ProductVariant
from .models import Cart, CartItem
from django.contrib import messages

def test_orders(request):
	return HttpResponse('Orders app is working!')

def cart_view(request):
	cart = None
	items = []
	total = 0
	if request.user.is_authenticated:
		cart = Cart.objects.filter(user=request.user).first()
	else:
		session_key = request.session.session_key
		if not session_key:
			request.session.create()
			session_key = request.session.session_key
		cart = Cart.objects.filter(session_key=session_key, user=None).first()
	if cart:
		items = cart.items.select_related('product', 'variant').all()
		total = sum(item.subtotal() for item in items)
	return render(request, 'orders/cart.html', {'cart': cart, 'items': items, 'total': total})

def get_or_create_cart(request):
	if request.user.is_authenticated:
		cart, created = Cart.objects.get_or_create(user=request.user)
	else:
		session_key = request.session.session_key
		if not session_key:
			request.session.create()
			session_key = request.session.session_key
		cart, created = Cart.objects.get_or_create(session_key=session_key, user=None)
	return cart

def add_to_cart(request):
	# determine if we should treat this as AJAX early so we can suppress messages
	is_ajax = (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
			   request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest')
	if request.method == 'POST':
		product_id = request.POST.get('product_id')
		variant_id = request.POST.get('variant')
		quantity = int(request.POST.get('quantity', 1))
		product = get_object_or_404(Product, id=product_id)
		variant = None
		price = product.price
		if variant_id:
			variant = get_object_or_404(ProductVariant, id=variant_id)
			price += variant.additional_price
		cart = get_or_create_cart(request)
		# enforce stock limits
		available_stock = variant.stock if variant else product.stock
		
		if available_stock <= 0:
			msg = f"'{product.name}' is out of stock."
			if not is_ajax:
				messages.error(request, msg)
			if is_ajax:
				return JsonResponse({'success': False, 'message': msg, 'cart_count': cart.total_items(), 'available_stock': available_stock})
			return redirect(request.META.get('HTTP_REFERER', 'products:shop'))
		
		# Block if stock is critically low (≤ 1)
		if available_stock <= 1:
			msg = f"'{product.name}' is critically low in stock and unavailable for orders."
			if not is_ajax:
				messages.error(request, msg)
			if is_ajax:
				return JsonResponse({'success': False, 'message': msg, 'cart_count': cart.total_items(), 'available_stock': available_stock})
			return redirect(request.META.get('HTTP_REFERER', 'products:shop'))
		# Check if item already exists
		cart_item = CartItem.objects.filter(cart=cart, product=product, variant=variant).first()
		existing_qty = cart_item.quantity if cart_item else 0
		space_left = available_stock - existing_qty
		if space_left <= 0:
			msg = f"Insufficient stock for '{product.name}'. Only {available_stock} left."
			if not is_ajax:
				messages.error(request, msg)
			if is_ajax:
				return JsonResponse({'success': False, 'message': msg, 'cart_count': cart.total_items(), 'available_stock': available_stock})
			return redirect(request.META.get('HTTP_REFERER', 'products:shop'))
		# determine actual addition amount
		add_qty = min(quantity, space_left)
		partial = add_qty < quantity
		if cart_item:
			cart_item.quantity += add_qty
			cart_item.save()
		else:
			CartItem.objects.create(cart=cart, product=product, variant=variant, quantity=add_qty, price=price)
		# Track add to cart activity
		user = request.user
		if user.is_authenticated:
			try:
				from users.models_activity import Activity
				Activity.objects.create(user=user, activity_type='cart_add', product=product)
			except Exception:
				pass
		if partial:
			msg = f"Only {add_qty} of '{product.name}' added due to limited stock (only {available_stock} available)."
			if not is_ajax:
				messages.warning(request, msg)
		else:
			msg = f"'{product.name}' added to cart."
			if not is_ajax:
				messages.success(request, msg)
		# Support both request.headers and the WSGI META key used by the test client
		if is_ajax:
			# remaining stock available for additional adds (inventory not decremented until checkout)
			remaining_stock = max(0, available_stock - (existing_qty + add_qty))
			return JsonResponse({
				'success': True,
				'message': msg,
				'partial': partial,
				'cart_count': cart.total_items(),
				'remaining_stock': remaining_stock,
				'available_stock': available_stock
			})
		return redirect(request.META.get('HTTP_REFERER', 'products:shop'))
	return redirect('products:shop')


def bulk_add_to_cart(request):
	"""Add multiple products to the cart at once. Expects POST with 'product_ids' as a list and optional 'quantity'."""
	is_ajax = (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
			    request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest')
	if request.method == 'POST':
		ids = request.POST.getlist('product_ids')
		quantity = int(request.POST.get('quantity', 1))
		if not ids:
			if not is_ajax:
				messages.warning(request, 'No products selected.')
			return redirect(request.META.get('HTTP_REFERER', 'products:shop'))
		cart = get_or_create_cart(request)
		added = 0
		for pid in ids:
			try:
				product = Product.objects.get(id=pid)
			except Product.DoesNotExist:
				continue
			available_stock = product.stock
			if available_stock <= 0:
				# skip out-of-stock items
				continue
			cart_item = CartItem.objects.filter(cart=cart, product=product).first()
			existing_qty = cart_item.quantity if cart_item else 0
			space_left = available_stock - existing_qty
			if space_left <= 0:
				continue
			add_qty = min(quantity, space_left)
			if cart_item:
				cart_item.quantity += add_qty
				cart_item.save()
			else:
				CartItem.objects.create(cart=cart, product=product, quantity=add_qty, price=product.price)
			added += 1
		# Track bulk add activity
		user = request.user
		if user.is_authenticated and added:
			try:
				from users.models_activity import Activity
				for pid in ids:
					try:
						prod = Product.objects.get(id=pid)
						Activity.objects.create(user=user, activity_type='cart_add', product=prod)
					except Exception:
						pass
			except Exception:
				pass
		messages.success(request, f'{added} product(s) added to cart.')
		return redirect(request.META.get('HTTP_REFERER', 'products:shop'))
	return redirect('products:shop')

def cart_update_view(request):
	"""Handles increment/decrement/remove actions on cart items. Returns JSON for AJAX requests, otherwise redirects."""
	if request.method == 'POST':
		item_id = request.POST.get('item_id')
		action = request.POST.get('action')
		item = get_object_or_404(CartItem, id=item_id)
		# Perform action
		if action == 'increment':
			item.quantity += 1
			item.save()
		elif action == 'decrement':
			if item.quantity > 1:
				item.quantity -= 1
				item.save()
		elif action == 'remove':
			item.delete()
		# If AJAX, return JSON with updated totals
		is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
		if is_ajax:
			# recompute cart totals
			cart = get_or_create_cart(request)
			items = cart.items.all() if cart else []
			total = sum(i.subtotal() for i in items) if items else 0
			cart_count = sum(i.quantity for i in items) if items else 0
			# If the item was removed, set quantity and subtotal to 0
			if action == 'remove':
				qty = 0
				item_subtotal = 0
			else:
				qty = item.quantity if item and hasattr(item, 'quantity') else 0
				item_subtotal = float(item.subtotal()) if item and hasattr(item, 'subtotal') else 0
			response = {
				'success': True,
				'item_id': item_id,
				'quantity': qty,
				'item_subtotal': item_subtotal,
				'cart_total': float(total),
				'cart_count': cart_count,
			}
			return JsonResponse(response)
		# Non-AJAX fallback
		return redirect('orders:cart')
	return redirect('orders:cart')


def validate_cart_items(request):
	"""
	AJAX endpoint to validate cart items against current product state.
	Returns JSON with:
	- Validation status for each item (in stock, out of stock, quantity exceeds available)
	- Price differences (current vs cart price)
	- Out of stock warnings
	- Quantity adjustment suggestions
	"""
	cart = get_or_create_cart(request)
	items = cart.items.all() if cart else []
	
	validation_result = {
		'success': True,
		'valid': True,  # True if all items are valid
		'items': [],
		'warnings': [],
		'messages': []
	}
	
	for cart_item in items:
		item_validation = {
			'item_id': cart_item.id,
			'product_id': cart_item.product.id if cart_item.product else None,
			'variant_id': cart_item.variant.id if cart_item.variant else None,
			'product_name': cart_item.product.name if cart_item.product else 'Unknown',
			'cart_quantity': cart_item.quantity,
			'cart_price': float(cart_item.price),
			'is_valid': True,
			'issues': []
		}
		
		try:
			# Check product availability
			product = cart_item.product
			if not product:
				item_validation['is_valid'] = False
				item_validation['issues'].append('Product no longer available')
				validation_result['valid'] = False
				validation_result['items'].append(item_validation)
				continue
			
			# Check current stock
			current_stock = cart_item.variant.stock if cart_item.variant else product.stock
			
			if current_stock <= 0:
				item_validation['is_valid'] = False
				item_validation['issues'].append('Out of stock')
				validation_result['valid'] = False
				validation_result['warnings'].append(
					f"{cart_item.product.name}: No longer in stock"
				)
			elif current_stock < cart_item.quantity:
				item_validation['is_valid'] = False
				item_validation['issues'].append(
					f'Only {current_stock} available (requested {cart_item.quantity})'
				)
				item_validation['available_quantity'] = current_stock
				validation_result['valid'] = False
				validation_result['warnings'].append(
					f"{cart_item.product.name}: Only {current_stock} available"
				)
			elif current_stock <= 1:
				item_validation['is_valid'] = False
				item_validation['issues'].append('Critically low stock - unavailable for orders')
				validation_result['valid'] = False
				validation_result['warnings'].append(
					f"{cart_item.product.name}: Critically low in stock and unavailable for orders"
				)
			
			item_validation['available_quantity'] = current_stock
			
			# Check price changes
			current_price = float(product.price)
			if current_price != float(cart_item.price):
				item_validation['price_changed'] = True
				item_validation['current_price'] = current_price
				item_validation['price_difference'] = current_price - float(cart_item.price)
				
				old_subtotal = float(cart_item.price) * cart_item.quantity
				new_subtotal = current_price * cart_item.quantity
				subtotal_diff = new_subtotal - old_subtotal
				
				if subtotal_diff > 0:
					validation_result['warnings'].append(
						f"{cart_item.product.name}: Price increased by ₦{subtotal_diff:.2f}"
					)
				else:
					validation_result['messages'].append(
						f"{cart_item.product.name}: Price decreased by ₦{abs(subtotal_diff):.2f}"
					)
		
		except Exception as e:
			item_validation['is_valid'] = False
			item_validation['issues'].append(f'Error validating item: {str(e)}')
			validation_result['valid'] = False
		
		validation_result['items'].append(item_validation)
	
	if validation_result['valid']:
		validation_result['message'] = 'All items are valid and ready for checkout'
	else:
		validation_result['message'] = f'Found {len([i for i in validation_result["items"] if not i["is_valid"]])} issue(s) with cart items'
	
	return JsonResponse(validation_result)


def order_confirmation_view(request, order_id, token):
    order = get_object_or_404(Order, id=order_id)
    if order.confirmation_token != token:
        if request.user.is_authenticated and order.user == request.user:
            pass
        else:
            return redirect('core:home')
    if request.user.is_authenticated and order.user and order.user != request.user:
        return redirect('core:home')
    items = order.items.select_related('product', 'variant').all()
    payment_method = order.payment_method
    payment_status = 'success' if order.status in ('Processing', 'Shipped', 'Delivered', 'Completed') else 'pending'
    bank_name = 'GTBank'
    account_name = 'OD Ltd'
    account_number = '0123456789'
    try:
        from core.models import SiteContent
        _sc = SiteContent.objects.filter(key='checkout').first()
        if _sc:
            if _sc.bank_name:
                bank_name = _sc.bank_name
            if _sc.account_name:
                account_name = _sc.account_name
            if _sc.account_number:
                account_number = _sc.account_number
    except Exception:
        pass
    context = {
        'order': order,
        'items': items,
        'payment_method': payment_method,
        'payment_status': payment_status,
        'bank_name': bank_name,
        'account_name': account_name,
        'account_number': account_number,
        'token': token,
    }
    return render(request, 'orders/order_success.html', context)


def download_order_pdf(request, order_id, token):
    """Generate a downloadable PDF confirmation/invoice for an order (server-side via reportlab)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                    TableStyle, HRFlowable)
    from reportlab.lib.enums import TA_CENTER

    order = get_object_or_404(Order, id=order_id)

    # Same access control as the confirmation page
    if order.confirmation_token != token:
        if request.user.is_authenticated and order.user == request.user:
            pass
        else:
            return redirect('core:home')
    if request.user.is_authenticated and order.user and order.user != request.user:
        return redirect('core:home')

    items = order.items.select_related('product', 'variant').all()

    def money(value):
        try:
            return 'NGN ' + '{:,.2f}'.format(float(value))
        except (TypeError, ValueError):
            return '-'

    payment_method_label = {
        'paystack': 'Paystack',
        'manual': 'Bank Transfer',
        'pay_on_delivery': 'Pay on Delivery',
    }.get(order.payment_method, (order.payment_method or '').capitalize() or 'N/A')

    payment_status = 'Confirmed' if order.status in ('Processing', 'Shipped', 'Delivered', 'Completed') else 'Processing'
    delivery_option = order.get_delivery_option_display() if hasattr(order, 'get_delivery_option_display') else (order.delivery_option or '-')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="OlidStores_Order_%s.pdf"' % order.number

    brand = colors.HexColor('#8B7355')
    gold = colors.HexColor('#D4AF37')
    dark = colors.HexColor('#1f2937')
    light = colors.HexColor('#f3f4f6')
    grey = colors.HexColor('#6b7280')

    doc = SimpleDocTemplate(
        response, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title='Olid Stores Order %s' % order.number,
    )
    base = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleX', parent=base['Title'], textColor=brand, fontSize=22, spaceAfter=2)
    sub_style = ParagraphStyle('SubX', parent=base['Normal'], textColor=grey, fontSize=10, alignment=TA_CENTER)
    h_style = ParagraphStyle('HX', parent=base['Heading3'], textColor=dark, fontSize=12, spaceBefore=10, spaceAfter=4)
    normal = ParagraphStyle('NX', parent=base['Normal'], fontSize=9.5, leading=13)
    small = ParagraphStyle('SX', parent=base['Normal'], fontSize=8.5, textColor=grey, leading=11)
    cell = ParagraphStyle('CX', parent=base['Normal'], fontSize=9, leading=12)

    story = []
    story.append(Paragraph('OLID STORES', title_style))
    story.append(Paragraph('Order Confirmation', sub_style))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width='100%', thickness=2, color=gold))
    story.append(Spacer(1, 10))

    meta = [
        ['Order Number', order.number, 'Date', order.created_at.strftime('%B %d, %Y')],
        ['Order Status', order.status, 'Payment', '%s (%s)' % (payment_method_label, payment_status)],
    ]
    meta_tbl = Table(meta, colWidths=[33 * mm, 52 * mm, 28 * mm, 61 * mm])
    meta_tbl.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 9),
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 9),
        ('FONT', (2, 0), (2, -1), 'Helvetica-Bold', 9),
        ('TEXTCOLOR', (0, 0), (0, -1), grey),
        ('TEXTCOLOR', (2, 0), (2, -1), grey),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, -1), 0.4, light),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 8))

    story.append(Paragraph('Order Items', h_style))
    data = [['Product', 'Qty', 'Unit Price', 'Subtotal']]
    for it in items:
        name = it.product.name
        if it.variant:
            name += ' (%s)' % it.variant.name
        unit = money(it.subtotal / it.quantity) if it.quantity else money(it.subtotal)
        data.append([
            Paragraph(name, cell),
            str(it.quantity),
            Paragraph(unit, cell),
            Paragraph(money(it.subtotal), cell),
        ])
    items_tbl = Table(data, colWidths=[90 * mm, 18 * mm, 33 * mm, 33 * mm], repeatRows=1)
    items_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), brand),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9),
        ('FONT', (0, 1), (-1, -1), 'Helvetica', 9),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, light]),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#e5e7eb')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(items_tbl)
    story.append(Spacer(1, 8))

    totals = [['Subtotal', money(order.total)]]
    if order.delivery_fee:
        totals.append(['Delivery Fee (%s)' % delivery_option, money(order.delivery_fee)])
    totals.append(['Grand Total', money(order.grand_total)])
    tot_tbl = Table(totals, colWidths=[120 * mm, 54 * mm])
    tot_tbl.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 9.5),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEABOVE', (0, -1), (-1, -1), 1, gold),
        ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold', 11),
        ('TEXTCOLOR', (0, -1), (-1, -1), brand),
    ]))
    story.append(tot_tbl)
    story.append(Spacer(1, 10))

    story.append(Paragraph('Delivery Details', h_style))
    deliv = [
        ['Full Name', order.full_name or '-'],
        ['Phone', order.phone or '-'],
        ['Delivery Option', delivery_option],
        ['Address', order.delivery_address or '-'],
    ]
    if order.notes:
        deliv.append(['Notes', order.notes])
    deliv_tbl = Table(deliv, colWidths=[40 * mm, 134 * mm])
    deliv_tbl.setStyle(TableStyle([
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 9),
        ('FONT', (1, 0), (1, -1), 'Helvetica', 9),
        ('TEXTCOLOR', (0, 0), (0, -1), grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, -1), 0.4, light),
    ]))
    story.append(deliv_tbl)
    story.append(Spacer(1, 14))

    story.append(HRFlowable(width='100%', thickness=0.5, color=light))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        'Thank you for shopping with Olid Stores. For support, contact support@olidstores.com or +234 800 000 0000.',
        small))

    doc.build(story)
    return response

from django.contrib.auth.decorators import login_required
from .models import Order

@login_required
def order_history_view(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    search_query = request.GET.get('search', '')
    if search_query:
        from django.db.models import Q
        orders = orders.filter(
            Q(id__icontains=search_query) |
            Q(status__icontains=search_query) |
            Q(tracking_number__icontains=search_query)
        )
    return render(request, 'orders/order_history.html', {'orders': orders, 'search_query': search_query})

@login_required
def order_detail_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})
