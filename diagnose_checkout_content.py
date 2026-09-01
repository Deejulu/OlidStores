"""Check checkout page content"""
import urllib.request

r = urllib.request.urlopen('http://127.0.0.1:8000/checkout/', timeout=10)
html = r.read().decode()

# Check for key elements
print('Has checkout-page class:', 'checkout-page' in html)
print('Has checkout-form:', 'checkout-form' in html)
print('Has payment-method:', 'payment_method' in html)
print('Has Paystack text:', 'Paystack' in html)

# Print a snippet of the HTML around the payment section
import re
match = re.search(r'<div class="card-body p-4">.{0,1000}', html, re.DOTALL)
if match:
    print('\nPayment section snippet:')
    print(match.group()[:500])
