"""Check checkout page with items in cart"""
import urllib.request
import http.cookiejar

# Create a cookie jar
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Get the shop page to get a CSRF token
req = urllib.request.Request('http://127.0.0.1:8000/shop/')
resp = opener.open(req, timeout=10)

# Get CSRF token
csrf = None
for cookie in cj:
    if cookie.name == 'csrftoken':
        csrf = cookie.value
        break

print(f'CSRF token: {csrf[:20]}...' if csrf else 'CSRF token: NOT FOUND')

# Add item to cart
import urllib.parse
data = urllib.parse.urlencode({'product_id': '780', 'quantity': '1'}).encode()
req = urllib.request.Request('http://127.0.0.1:8000/cart/add/', data=data, headers={
    'X-CSRFToken': csrf,
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'http://127.0.0.1:8000/shop/'
})
resp = opener.open(req, timeout=10)
print(f'Add to cart response: {resp.read().decode()[:100]}')

# Now check checkout page
req = urllib.request.Request('http://127.0.0.1:8000/checkout/')
resp = opener.open(req, timeout=10)
html = resp.read().decode()

# Check for radio buttons
import re
print(f'Has paystack_method: {"paystack_method" in html}')
print(f'Has manual_method: {"manual_method" in html}')
print(f'Has pod_method: {"pod_method" in html}')
print(f'Has Bank Transfer: {"Bank Transfer" in html}')
print(f'Has Pay on Delivery: {"Pay on Delivery" in html}')

# Check for DEBUG output
match = re.search(r'DEBUG:.*?', html)
print(f'Debug output: {match.group() if match else "NOT FOUND"}')
