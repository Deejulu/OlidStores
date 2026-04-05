import hmac
import hashlib
import json
import requests
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Order, OrderItem, PaymentTransaction, CheckoutSettings

from .utils import verify_paystack_reference as _verify_paystack_reference
# Replaced inline verifier with shared utils.verify_paystack_reference
# _verify_paystack_reference now returns the full JSON or None on error.

from django.contrib.auth.decorators import login_required

@login_required(login_url='/accounts/login/')
def checkout_view(request):
	# ...existing code...
	cart = None
	items = []
	total = 0
	# load admin-configured fees (fallback to settings or CheckoutSettings)
	cs = CheckoutSettings.objects.first()
	print('DEBUG CheckoutSettings cs', cs)
	if cs:
		print('DEBUG cs.fees', cs.delivery_fee_24h, cs.delivery_fee_2d)
	delivery_fee_24h = cs.delivery_fee_24h if cs else getattr(settings, 'DELIVERY_FEE_24H', 0)
	delivery_fee_2d = cs.delivery_fee_2d if cs else getattr(settings, 'DELIVERY_FEE_2D', 0)
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

	# Block access if any cart item exceeds available stock
	if cart:
		items = cart.items.select_related('product', 'variant').all()
		for item in items:
			if item.variant:
				if item.variant.stock < item.quantity:
					messages.error(request, f"Insufficient stock for {item.variant.name}. Please adjust your cart.")
					return redirect('orders:cart')
			else:
				if item.product.stock < item.quantity:
					messages.error(request, f"Insufficient stock for {item.product.name}. Please adjust your cart.")
					return redirect('orders:cart')
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
		delivery_option = request.POST.get('delivery_option')
		delivery_fee = 0
		if delivery_option == '24h':
			delivery_fee = delivery_fee_24h
		elif delivery_option == '2d':
			delivery_fee = delivery_fee_2d

		if cart:
			items = cart.items.select_related('product', 'variant').all()
			from decimal import Decimal
			base_total = sum(item.subtotal() for item in items)
			total = base_total + (delivery_fee or Decimal('0.00'))

		if payment_method == 'manual':
			# Manual payment: check and reserve stock, then create order as pending, save receipt
			print('DEBUG manual payment delivery_option', delivery_option, 'delivery_fee', delivery_fee, 'delivery_fee_24h', delivery_fee_24h, 'delivery_fee_2d', delivery_fee_2d)
			from django.db import transaction
			with transaction.atomic():
				for item in items:
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
					notes=notes or '',
					receipt=receipt_file
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
			return redirect('orders:cart')
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
			print('DEBUG verify resp', resp)
			if not resp or not resp.get('status'):
				messages.error(request, 'Payment verification failed. Please contact support.')
				return redirect('orders:checkout')
			data = resp.get('data', {})
			print('DEBUG data', data)
			# Check transaction status and amount
			if data.get('status') == 'success':
				print('DEBUG entered success block')
				amount_kobo = int(data.get('amount', 0))
				expected_kobo = int(round(float(total) * 100))
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
					notes=notes
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
				pt = PaymentTransaction.objects.create(
					reference=paystack_reference,
					order=order,
					amount=float(data.get('amount', 0)) / 100.0,
					currency=data.get('currency', 'NGN'),
					status=data.get('status', ''),
					raw_response=data
				)
				print('DEBUG created order', order.id, 'pt', pt.reference)
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
			return redirect('orders:cart')
			# Payment not successful
			messages.error(request, 'Payment not successful.')
			return redirect('orders:checkout')
		else:
			messages.error(request, 'Invalid payment method or missing information.')
	if cart:
		items = cart.items.select_related('product', 'variant').all()
		total = sum(item.subtotal() for item in items)
		
		# Get bank transfer details from SiteContent
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
		'cart': cart,
		'items': items,
		'base_total': total,
		'total': total,  # may be adjusted on the client when delivery is selected
		'PAYSTACK_PUBLIC': settings.PAYSTACK_PUBLIC,
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
	if not request.user.is_authenticated:
		msg = "You must be logged in to add items to your cart."
		if is_ajax:
			return JsonResponse({'success': False, 'message': msg, 'cart_count': 0})
		messages.error(request, msg)
		return redirect('login')
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
