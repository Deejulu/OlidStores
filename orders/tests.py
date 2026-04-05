from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings
from unittest import mock
import json, hmac, hashlib

from products.models import Product, Category
from django.contrib.auth import get_user_model
from .models import Cart, CartItem, Order, PaymentTransaction

class PaystackIntegrationTests(TestCase):
	def setUp(self):
		self.client = Client()
		# create auth user and login for cart operations
		User = get_user_model()
		self.user = User.objects.create_user(username='testuser', password='password')
		success = self.client.login(username='testuser', password='password')
		self.assertTrue(success, "failed to log in test user")
		self.category = Category.objects.create(name='TestCat')
		self.product = Product.objects.create(name='Test Product', price=50.00, description='Desc', category=self.category, stock=10)

	@mock.patch('orders.views._verify_paystack_reference')
	def test_paystack_verify_creates_order(self, mock_verify):
		# prepare cart and attach to client session
		session = self.client.session
		session.save()
		session_key = session.session_key
		cart = Cart.objects.create(session_key=session_key)
		CartItem.objects.create(cart=cart, product=self.product, quantity=2, price=self.product.price)
		# mock paystack verify response
		total = cart.total_price()
		mock_verify.return_value = {'status': True, 'data': {'status': 'success', 'amount': int(total * 100), 'currency': 'NGN', 'reference': 'test-ref-123'}}
		# POST to checkout with paystack_reference
		response = self.client.post(reverse('orders:checkout'), {
			'payment_method': 'paystack',
			'paystack_reference': 'test-ref-123',
			'full_name': 'John Doe',
			'phone': '0800000000',
			'email': 'a@b.com',
			'delivery_address': '123 Street',
		})
		print('DEBUG response', response.status_code, response.content[:200])
		self.assertEqual(Order.objects.count(), 1)
		self.assertEqual(PaymentTransaction.objects.count(), 1)
		order = Order.objects.first()
		pt = PaymentTransaction.objects.first()
		self.assertEqual(pt.order, order)
		# cart items should be cleared
		cart.refresh_from_db()
		self.assertEqual(cart.items.count(), 0)

	@mock.patch('orders.utils.verify_paystack_reference')
	def test_paystack_webhook_signature_and_record(self, mock_verify):
		payload = {
			'event': 'charge.success',
			'data': {'reference': 'hook-ref-1', 'amount': 5000, 'currency': 'NGN', 'status': 'success'}
		}
		body = json.dumps(payload).encode()
		sig = hmac.new(settings.PAYSTACK_SECRET.encode(), body, hashlib.sha512).hexdigest()
		# mock verification to return a successful verify payload
		mock_verify.return_value = {'status': True, 'data': {'reference': 'hook-ref-1', 'amount': 5000, 'currency': 'NGN', 'status': 'success'}}
		resp = self.client.post(reverse('orders:paystack_webhook'), data=body, content_type='application/json', **{'HTTP_X_PAYSTACK_SIGNATURE': sig})
		self.assertEqual(resp.status_code, 200)
		# Since webhook processing calls verify and then creates the transaction, ensure record exists
		self.assertTrue(PaymentTransaction.objects.filter(reference='hook-ref-1').exists())

	@mock.patch('orders.utils.verify_paystack_reference')
	def test_verify_command_updates_transaction(self, mock_verify):
		# create a transaction with blank status
		tx = PaymentTransaction.objects.create(reference='cmd-test-1', status='', amount=0.0, currency='NGN', raw_response={})
		# mock verify to return success
		mock_verify.return_value = {'status': True, 'data': {'reference': 'cmd-test-1', 'amount': 4500, 'currency': 'NGN', 'status': 'success'}}
		from django.core.management import call_command
		call_command('verify_paystack_transactions', '--limit', '10')
		tx.refresh_from_db()
		self.assertEqual(tx.status, 'success')
		self.assertEqual(tx.amount, 45.0)

	def test_create_orders_from_transactions_command(self):
		# create a transaction without an order
		tx = PaymentTransaction.objects.create(reference='create-test-1', status='success', amount=60.0, currency='NGN', raw_response={})
		from django.core.management import call_command
		call_command('create_orders_from_transactions', '--limit', '10')
		tx.refresh_from_db()
		self.assertIsNotNone(tx.order)

	def test_stock_decrements_on_paystack_checkout(self):
		# setup product with stock
		from products.models import Category
		cat = Category.objects.create(name='Cat2')
		prod = Product.objects.create(name='Stocky', price=30.0, description='x', category=cat, stock=2)
		# attach cart to session
		session = self.client.session
		session.save()
		session_key = session.session_key
		cart = Cart.objects.create(session_key=session_key)
		CartItem.objects.create(cart=cart, product=prod, quantity=2, price=prod.price)
		# mock paystack verify response
		with mock.patch('orders.views._verify_paystack_reference') as mock_verify:
			mock_verify.return_value = {'status': True, 'data': {'status': 'success', 'amount': int(cart.total_price() * 100), 'currency': 'NGN', 'reference': 'stk-1'}}
			response = self.client.post(reverse('orders:checkout'), {
				'payment_method': 'paystack',
				'paystack_reference': 'stk-1',
				'full_name': 'John',
				'phone': '080',
				'email': 'a@b.com',
				'delivery_address': 'here',
			})
			prod.refresh_from_db()
			self.assertEqual(prod.stock, 0)
			self.assertEqual(Order.objects.count(), 1)

	def test_insufficient_stock_prevents_order(self):
		from products.models import Category
		cat = Category.objects.create(name='Cat3')
		prod = Product.objects.create(name='Low', price=20.0, description='x', category=cat, stock=1)
		session = self.client.session
		session.save()
		session_key = session.session_key
		cart = Cart.objects.create(session_key=session_key)
		CartItem.objects.create(cart=cart, product=prod, quantity=2, price=prod.price)
		# Attempt manual checkout
		response = self.client.post(reverse('orders:checkout'), {
			'payment_method': 'manual',
			'full_name': 'John',
			'phone': '080',
			'email': 'a@b.com',
			'delivery_address': 'here',
		})
		self.assertEqual(Order.objects.count(), 0)
		prod.refresh_from_db()
		self.assertEqual(prod.stock, 1)

	def test_webhook_event_persist_and_process(self):
		payload = {
			'event': 'charge.success',
			'data': {'reference': 'hook-persist-1', 'amount': 5000, 'currency': 'NGN', 'status': 'success'}
		}
		body = json.dumps(payload).encode()
		sig = hmac.new(settings.PAYSTACK_SECRET.encode(), body, hashlib.sha512).hexdigest()
		resp = self.client.post(reverse('orders:paystack_webhook'), data=body, content_type='application/json', **{'HTTP_X_PAYSTACK_SIGNATURE': sig})
		self.assertEqual(resp.status_code, 200)
		from orders.models import WebhookEvent
		self.assertTrue(WebhookEvent.objects.filter(reference='hook-persist-1').exists())
		# mock verification so process_webhook_events will create a transaction
		with mock.patch('orders.utils.verify_paystack_reference') as mock_verify:
			mock_verify.return_value = {'status': True, 'data': {'reference': 'hook-persist-1', 'amount': 5000, 'currency': 'NGN', 'status': 'success'}}
			from django.core.management import call_command
			call_command('process_webhook_events', '--limit', '10')
		self.assertTrue(PaymentTransaction.objects.filter(reference='hook-persist-1').exists())

	def test_bulk_add_to_cart(self):
		# prepare products
		cat = Category.objects.create(name='BulkCat')
		p1 = Product.objects.create(name='Bulk1', slug='bulk1', price=10.0, category=cat, stock=5)
		p2 = Product.objects.create(name='Bulk2', slug='bulk2', price=15.0, category=cat, stock=3)
		# post bulk add
		session = self.client.session
		session.save()
		r = self.client.post('/cart/bulk_add/', {'product_ids': [str(p1.id), str(p2.id)], 'quantity': 1}, HTTP_HOST='127.0.0.1')
		self.assertEqual(r.status_code, 302)
		# check cart items
		from .models import Cart
		# user is logged in so cart should be associated with user
		cart = Cart.objects.filter(user=self.user).first()
		self.assertIsNotNone(cart)
		items = list(cart.items.all())
		self.assertEqual(len(items), 2)

	def test_add_to_cart_ajax(self):
		# Ensure AJAX add_to_cart returns JSON and creates a cart item
		r = self.client.post('/cart/add/', {'product_id': str(self.product.id), 'quantity': 1}, HTTP_X_REQUESTED_WITH='XMLHttpRequest', HTTP_HOST='127.0.0.1')
		self.assertEqual(r.status_code, 200)
		data = r.json()
		self.assertTrue(data.get('success'))
		cart = Cart.objects.filter(user=self.user).first()
		self.assertIsNotNone(cart)
		self.assertEqual(cart.total_items(), 1)

	def test_add_to_cart_out_of_stock(self):
		# Out of stock product should not be added
		from products.models import Category
		cat = Category.objects.create(name='OOS')
		prod = Product.objects.create(name='OOSProd', price=10.0, description='x', category=cat, stock=0)
		r = self.client.post('/cart/add/', {'product_id': str(prod.id), 'quantity': 1}, HTTP_X_REQUESTED_WITH='XMLHttpRequest', HTTP_HOST='127.0.0.1')
		self.assertEqual(r.status_code, 200)
		data = r.json()
		self.assertFalse(data.get('success'))
		self.assertIn('out of stock', data.get('message').lower())
		from .models import Cart
		cart = Cart.objects.filter(user=self.user).first()
		# cart may exist but should contain no items
		self.assertIsNotNone(cart)
		self.assertEqual(cart.total_items(), 0)

	def test_add_to_cart_partial_stock(self):
		# Adding more than available should only add up to available stock
		from products.models import Category
		cat = Category.objects.create(name='Partial')
		prod = Product.objects.create(name='PartialProd', price=10.0, description='x', category=cat, stock=1)
		r = self.client.post('/cart/add/', {'product_id': str(prod.id), 'quantity': 2}, HTTP_X_REQUESTED_WITH='XMLHttpRequest', HTTP_HOST='127.0.0.1')
		self.assertEqual(r.status_code, 200)
		data = r.json()
		self.assertTrue(data.get('success'))
		self.assertTrue(data.get('partial'))
		from .models import Cart
		cart = Cart.objects.filter(user=self.user).first()
		self.assertIsNotNone(cart)
		self.assertEqual(cart.total_items(), 1)
		ci = cart.items.first()

	def test_ajax_add_does_not_leave_messages(self):
		# perform an AJAX add and then visit a category page; there should be
		# no django message alerts in the resulting HTML
		from products.models import Category
		cat = Category.objects.create(name='MsgCat', slug='msgcat')
		prod = Product.objects.create(name='MsgProd', slug='msgprod', price=5.0, category=cat, stock=10)
		session = self.client.session
		session.save()
		# add via AJAX
		r = self.client.post('/cart/add/', {'product_id': str(prod.id), 'quantity': 1}, HTTP_X_REQUESTED_WITH='XMLHttpRequest', HTTP_HOST='127.0.0.1')
		self.assertEqual(r.status_code, 200)
		data = r.json()
		self.assertTrue(data.get('success'))
		# cart record should belong to user and have one item
		from .models import Cart
		cart = Cart.objects.filter(user=self.user).first()
		self.assertIsNotNone(cart)
		self.assertEqual(cart.total_items(), 1)
		# now load category page normally
		r2 = self.client.get(f'/shop/?category={cat.slug}', HTTP_HOST='127.0.0.1')
		self.assertEqual(r2.status_code, 200)
		# messages container should be empty / not contain alert divs
		self.assertNotIn(b'<div class="alert-message', r2.content)

	def test_cart_update_ajax(self):
		# Prepare a cart with one item and test increment/decrement/remove via AJAX
		session = self.client.session
		session.save()
		session_key = session.session_key
		cart = Cart.objects.create(session_key=session_key)
		ci = CartItem.objects.create(cart=cart, product=self.product, quantity=1, price=self.product.price)
		# increment
		r = self.client.post('/cart/update/', {'item_id': ci.id, 'action': 'increment'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest', HTTP_HOST='127.0.0.1')
		self.assertEqual(r.status_code, 200)
		data = r.json()
		self.assertTrue(data.get('success'))
		self.assertEqual(int(data.get('quantity')), 2)
		# decrement
		r = self.client.post('/cart/update/', {'item_id': ci.id, 'action': 'decrement'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest', HTTP_HOST='127.0.0.1')
		self.assertEqual(r.status_code, 200)
		data = r.json()
		self.assertEqual(int(data.get('quantity')), 1)
		# remove
		r = self.client.post('/cart/update/', {'item_id': ci.id, 'action': 'remove'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest', HTTP_HOST='127.0.0.1')
		self.assertEqual(r.status_code, 200)
		data = r.json()
		self.assertEqual(int(data.get('quantity')), 0)

	def test_delivery_fee_from_checkout_settings_manual(self):
		# configure admin checkout settings
		from .models import CheckoutSettings
		CheckoutSettings.objects.create(delivery_fee_24h=25.00, delivery_fee_2d=10.00)
		# prepare cart and attach to client session
		session = self.client.session
		session.save()
		session_key = session.session_key
		cart = Cart.objects.create(session_key=session_key)
		CartItem.objects.create(cart=cart, product=self.product, quantity=1, price=self.product.price)
		# submit manual checkout selecting 24h delivery
		r = self.client.post(reverse('orders:checkout'), {
			'payment_method': 'manual',
			'full_name': 'Jane',
			'phone': '0700',
			'email': 'j@e.com',
			'delivery_address': 'addr',
			'delivery_option': '24h',
		}, HTTP_HOST='127.0.0.1')
		self.assertEqual(Order.objects.count(), 1)
		order = Order.objects.first()
		self.assertEqual(float(order.delivery_fee), 25.00)
		self.assertEqual(order.delivery_option, '24h')

	def test_delivery_fee_from_sitecontent_manual(self):
		# configure site content checkout fees
		from core.models import SiteContent
		sc, _ = SiteContent.objects.get_or_create(key='checkout')
		sc.delivery_fee_24h = 30.00
		sc.delivery_fee_2d = 12.00
		sc.save()
		# prepare cart and attach to client session
		session = self.client.session
		session.save()
		session_key = session.session_key
		cart = Cart.objects.create(session_key=session_key)
		CartItem.objects.create(cart=cart, product=self.product, quantity=1, price=self.product.price)
		# submit manual checkout selecting 24h delivery
		r = self.client.post(reverse('orders:checkout'), {
			'payment_method': 'manual',
			'full_name': 'Jane2',
			'phone': '0700',
			'email': 'j2@e.com',
			'delivery_address': 'addr',
			'delivery_option': '24h',
		}, HTTP_HOST='127.0.0.1')
		self.assertEqual(Order.objects.count(), 1)
		order = Order.objects.first()
		self.assertEqual(float(order.delivery_fee), 30.00)
		self.assertEqual(order.delivery_option, '24h')

