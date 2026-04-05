from django.test import Client
from products.models import Product, Category
from orders.models import Cart, CartItem
import orders.utils as u

c = Client()
cat = Category.objects.create(name='DbgCat')
prod = Product.objects.create(name='DbgProd', price=50.0, description='D', category=cat, stock=10)
session = c.session
session.save()
session_key = session.session_key
cart = Cart.objects.create(session_key=session_key)
CartItem.objects.create(cart=cart, product=prod, quantity=1, price=prod.price)

class MockResp:
    status_code = 200
    def json(self):
        return {'status': True, 'data': {'status': 'success', 'amount': int(cart.total_price()*100), 'currency': 'NGN', 'reference': 'dbg-ref'}}

u.requests.get = lambda *a, **k: MockResp()
resp = c.post('/cart/checkout/', {'payment_method': 'paystack', 'paystack_reference': 'dbg-ref', 'full_name': 'A', 'phone': '1', 'email': 'a@b.c', 'delivery_address': 'here'})
print('status', resp.status_code)
print('Order count', __import__('orders.models', fromlist=['Order']).Order.objects.count())
print('Cart items', Cart.objects.get(id=cart.id).items.count())
