"""Check checkout page content"""
import urllib.request

r = urllib.request.urlopen('http://127.0.0.1:8000/checkout/', timeout=10)
html = r.read().decode()

# Find Paystack text and surrounding context
import re
match = re.search(r'.{0,200}Paystack.{0,200}', html)
if match:
    print('Context around Paystack:')
    print(match.group())
