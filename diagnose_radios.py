"""Check which radio buttons exist in checkout HTML"""
import urllib.request
import re

r = urllib.request.urlopen('http://127.0.0.1:8000/checkout/', timeout=10)
html = r.read().decode()

# Check for paystack_method
match = re.search(r'id="paystack_method"', html)
print('Paystack radio:', 'FOUND' if match else 'NOT FOUND')

# Check for manual_method
match = re.search(r'id="manual_method"', html)
print('Manual radio:', 'FOUND' if match else 'NOT FOUND')

# Check for pod_method
match = re.search(r'id="pod_method"', html)
print('POD radio:', 'FOUND' if match else 'NOT FOUND')

# Check for Bank Transfer text
print('Bank Transfer text:', 'FOUND' if 'Bank Transfer' in html else 'NOT FOUND')

# Check for Pay on Delivery text
print('Pay on Delivery text:', 'FOUND' if 'Pay on Delivery' in html else 'NOT FOUND')
