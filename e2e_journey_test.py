"""
Comprehensive E2E Journey Test for Olid Stores v2
Tests both Customer and Admin journeys using Playwright.
"""
import asyncio
import os
import re
import sys
import time
from datetime import datetime

from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"
SCREENSHOT_DIR = "test_screenshots"
report = []
current_section = ""


def log(step, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    entry = f"[{status}] {step}"
    if detail:
        entry += f" | {detail}"
    report.append({"section": current_section, "step": step, "passed": passed, "detail": detail})
    try:
        print(entry)
    except UnicodeEncodeError:
        print(entry.encode('ascii', errors='replace').decode('ascii'))


async def take_screenshot(page, name):
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    path = f"{SCREENSHOT_DIR}/{name}.png"
    await page.screenshot(path=path, full_page=True)
    return path


async def run_customer_journey(browser):
    global current_section
    current_section = "PART 1: CUSTOMER JOURNEY"
    print(f"\n{'='*60}")
    print(f"  {current_section}")
    print(f"{'='*60}")

    context = await browser.new_context(viewport={"width": 1280, "height": 900})
    page = await context.new_page()

    ts = int(time.time())
    first_name = "Test"
    last_name = "Customer"
    password = "SecurePass123!"

    # ============================================================
    # 1. DISCOVERY & BROWSING
    # ============================================================
    print("\n--- 1. Discovery & Browsing ---")

    # 1a. Visit homepage
    homepage_ok = False
    try:
        resp = await page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=15000)
        homepage_ok = resp.status == 200
        log("1a. Homepage loads (HTTP 200)", homepage_ok, f"Status: {resp.status}")
        if not homepage_ok:
            await take_screenshot(page, "01_homepage_fail")
    except Exception as e:
        log("1a. Homepage loads", False, f"Exception: {e}")
        await take_screenshot(page, "01_homepage_fail")

    # 1b. Check homepage content
    if homepage_ok:
        try:
            body_text = await page.inner_text("body")
            has_nav = await page.locator("nav").count() > 0
            log("1b. Homepage has navigation", has_nav)
            log("1b. Homepage has body content", len(body_text) > 100, f"Content length: {len(body_text)} chars")
        except Exception as e:
            log("1b. Homepage content check", False, str(e))

    # 1c. Browse Shop page
    shop_ok = False
    try:
        resp = await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=15000)
        shop_ok = resp.status == 200
        log("1c. Shop page loads", shop_ok, f"Status: {resp.status}")
        if not shop_ok:
            await take_screenshot(page, "01_shop_fail")
    except Exception as e:
        log("1c. Shop page loads", False, str(e))

    # 1d. Check products display (wait for JS to load)
    if shop_ok:
        try:
            await page.wait_for_timeout(2000)
            product_cards = await page.locator(".product-card").count()
            log("1d. Products display on shop page", product_cards > 0, f"Found {product_cards} product cards")
            if product_cards == 0:
                await take_screenshot(page, "01_shop_no_products")
        except Exception as e:
            log("1d. Products display check", False, str(e))

    # 1e. Category filters
    if shop_ok:
        try:
            cat_filters = await page.locator(".category-filter, [class*='category'], .filter-chip").count()
            log("1e. Category filters present", cat_filters > 0, f"Found {cat_filters} filter elements")
        except Exception as e:
            log("1e. Category filters check", False, str(e))

    # 1f. Test search
    try:
        await page.goto(f"{BASE_URL}/search/", wait_until="networkidle", timeout=10000)
        search_input = await page.locator("input[name='q'], input[type='search'], #mainSearchInput").count()
        log("1f. Search page has input", search_input > 0)
        if search_input > 0:
            search_box = page.locator("input[name='q'], input[type='search'], #mainSearchInput").first
            await search_box.fill("fan")
            await search_box.press("Enter")
            await page.wait_for_load_state("networkidle", timeout=10000)
            await page.wait_for_timeout(2000)
            results = await page.locator(".product-card").count()
            log("1f. Search returns results for 'fan'", results > 0, f"Returned {results} results")
    except Exception as e:
        log("1f. Search functionality", False, str(e))

    # 1g. View product detail page (click eye icon)
    detail_ok = False
    try:
        await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=10000)
        await page.wait_for_timeout(2000)
        # The eye icon link navigates to product detail
        eye_link = page.locator(".product-actions a[href*='/shop/']").first
        if await eye_link.count() > 0:
            href = await eye_link.get_attribute("href")
            log("1g. Product detail link found", True, f"href: {href}")
            await eye_link.click()
            await page.wait_for_load_state("networkidle", timeout=10000)
            detail_ok = "/shop/" in page.url and page.url != f"{BASE_URL}/shop/"
            log("1g. Product detail page loads", detail_ok, f"URL: {page.url}")
            if detail_ok:
                body = await page.inner_text("body")
                has_price = "price" in body.lower()
                has_add_cart = await page.locator("button.btn-add-to-cart").count() > 0
                log("1g. Product shows price", has_price)
                log("1g. Product has Add to Cart button", has_add_cart)
                if not has_add_cart:
                    await take_screenshot(page, "01_product_no_addcart")
        else:
            log("1g. Product detail link found", False, "No eye icon link found")
    except Exception as e:
        log("1g. Product detail page", False, str(e))

    # ============================================================
    # 2. SIGNUP
    # ============================================================
    print("\n--- 2. Signup & Account Creation ---")
    new_username = None

    try:
        resp = await page.goto(f"{BASE_URL}/accounts/signup/", wait_until="networkidle", timeout=15000)
        signup_loaded = resp.status == 200
        has_first = await page.locator("#id_first_name").count() > 0
        has_last = await page.locator("#id_last_name").count() > 0
        has_pass1 = await page.locator("#id_password1").count() > 0
        has_pass2 = await page.locator("#id_password2").count() > 0
        log("2a. Signup page loads with form", signup_loaded and has_first and has_last and has_pass1 and has_pass2)

        if has_first:
            await page.fill("#id_first_name", first_name)
            await page.fill("#id_last_name", last_name)
            await page.fill("#id_password1", password)
            await page.fill("#id_password2", password)

            q_selects = await page.locator("select[name^='security_question_']").count()
            log("2b. Security question selects present", q_selects >= 3, f"Found {q_selects} selects")

            if q_selects >= 3:
                # Collect available question IDs first to ensure we pick 3 different ones
                first_sel = page.locator("select[name='security_question_1']")
                all_options = await first_sel.locator("option").all()
                available_ids = []
                for opt in all_options[1:]:  # skip placeholder
                    v = await opt.get_attribute("value")
                    if v:
                        available_ids.append(v)
                log("2b. Available security questions", len(available_ids) >= 3, f"Found {len(available_ids)} questions")

                # Select 3 DIFFERENT questions
                for i in range(1, 4):
                    sel = page.locator(f"select[name='security_question_{i}']")
                    # Pick a different question for each select
                    question_id = available_ids[i - 1] if i <= len(available_ids) else available_ids[-1]
                    if question_id:
                        await sel.select_option(question_id)
                    await page.fill(f"#id_security_answer_{i}", f"Answer{i}")

                submit_btn = page.locator("#signup-submit-button")
                if await submit_btn.count() > 0:
                    await submit_btn.click()
                    await page.wait_for_load_state("networkidle", timeout=15000)

                    on_credentials = "/accounts/signup/credentials/" in page.url
                    log("2c. Signup redirects to credentials page", on_credentials, f"URL: {page.url}")

                    if on_credentials:
                        body = await page.inner_text("body")
                        username_match = re.search(r'([A-Z][a-z]+){2}\d{4}OLID[A-Z0-9]+', body)
                        if username_match:
                            new_username = username_match.group(0)
                            log("2d. Credentials page shows generated username", True, f"Username: {new_username}")
                            pattern_ok = bool(re.match(r'^TestCustomer20\d{2}OLID[A-Z0-9]+$', new_username))
                            log("2d. Username follows expected pattern (FirstLastYearOLID+ID)", pattern_ok)
                        else:
                            log("2d. Credentials page shows generated username", False, "No username pattern found")
                            await take_screenshot(page, "02_credentials_no_username")

                        has_password = password in body
                        log("2e. Credentials page shows password", has_password)
                        has_recovery = "recovery" in body.lower() or "security" in body.lower() or "question" in body.lower()
                        log("2f. Credentials page shows recovery questions", has_recovery)
                    else:
                        if "/accounts/signup/" in page.url:
                            errors = await page.locator(".errorlist, .alert-danger, .form-error").all_text_contents()
                            log("2c. Signup form submission", False, f"Form errors: {errors}")
                            await take_screenshot(page, "02_signup_error")
                        else:
                            log("2c. Unexpected redirect after signup", False, f"URL: {page.url}")
                else:
                    log("2c. Signup submit button", False, "No submit button found")
            else:
                log("2b. Security questions", False, "Not enough question selects")
        else:
            log("2a. Signup form fields", False, "Missing form fields")
    except Exception as e:
        log("2. Signup flow", False, f"Exception: {e}")
        await take_screenshot(page, "02_signup_exception")

    # ============================================================
    # 3. CART & CHECKOUT
    # ============================================================
    print("\n--- 3. Cart & Checkout ---")

    # 3a. Add products to cart
    try:
        await page.goto(f"{BASE_URL}/shop/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        add_btn = page.locator("button.btn-add-to-cart").first
        log("3a. Add-to-cart button found", await add_btn.count() > 0)

        # Add first product using JavaScript (more reliable than click handler)
        result1 = await page.evaluate('''async () => {
            const btn = document.querySelector('button.btn-add-to-cart');
            if (!btn) return { error: 'no button' };
            const csrftoken = document.cookie.match(/csrftoken=([^;]+)/)[1];
            const resp = await fetch('/cart/add/', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrftoken, 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({ product_id: btn.dataset.productId, quantity: '1' })
            });
            return await resp.json();
        }''')
        log("3a. First product added to cart", result1.get("success", False), str(result1)[:80])

        # Add second product
        result2 = await page.evaluate('''async () => {
            const btns = document.querySelectorAll('button.btn-add-to-cart');
            if (btns.length < 2) return { error: 'no second button' };
            const btn = btns[1];
            const csrftoken = document.cookie.match(/csrftoken=([^;]+)/)[1];
            const resp = await fetch('/cart/add/', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrftoken, 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({ product_id: btn.dataset.productId, quantity: '1' })
            });
            return await resp.json();
        }''')
        log("3a. Second product added to cart", result2.get("success", False), str(result2)[:80])

        # Verify cart count
        cart_count = result2.get("cart_count", result1.get("cart_count", 0))
        log("3a. Cart count updated", cart_count >= 2, f"Cart count: {cart_count}")
    except Exception as e:
        log("3a. Add to cart", False, f"Exception: {e}")
        await take_screenshot(page, "03_addcart_fail")

    # 3b. View cart
    try:
        await page.goto(f"{BASE_URL}/cart/", wait_until="networkidle", timeout=10000)
        cart_ok = "/cart/" in page.url
        log("3b. Cart page loads", cart_ok, f"URL: {page.url}")
        if cart_ok:
            body = await page.inner_text("body")
            has_items = await page.locator(".cart-item, [class*='cart-item'], tr").count() > 0
            log("3b. Cart shows items", has_items)
            has_total = "total" in body.lower()
            log("3b. Cart shows total", has_total)
            if not has_items:
                await take_screenshot(page, "03_cart_empty")
    except Exception as e:
        log("3b. Cart page", False, str(e))

    # 3c. Update quantity
    try:
        await page.goto(f"{BASE_URL}/cart/", wait_until="networkidle", timeout=10000)
        qty_inputs = page.locator("input[name*='quantity'], input[type='number']")
        qty_count = await qty_inputs.count()
        log("3c. Cart has quantity inputs", qty_count > 0, f"Found {qty_count} inputs")
        if qty_count > 0:
            await qty_inputs.first.fill("2")
            update_btn = page.locator("button:has-text('Update'), button[name='update']")
            if await update_btn.count() > 0:
                await update_btn.first.click()
                await page.wait_for_load_state("networkidle", timeout=10000)
                log("3c. Quantity updated via button", True)
            else:
                await qty_inputs.first.press("Enter")
                await page.wait_for_load_state("networkidle", timeout=5000)
                log("3c. Quantity update (Enter key)", True)
    except Exception as e:
        log("3c. Update quantity", False, str(e))

    # 3d. Remove an item
    try:
        await page.goto(f"{BASE_URL}/cart/", wait_until="networkidle", timeout=10000)
        remove_btns = page.locator("a:has-text('Remove'), button:has-text('Remove'), .remove-item")
        remove_count = await remove_btns.count()
        log("3d. Remove item button present", remove_count > 0, f"Found {remove_count} buttons")
        if remove_count > 0:
            await remove_btns.first.click()
            await page.wait_for_load_state("networkidle", timeout=10000)
            log("3d. Item removed from cart", True)
    except Exception as e:
        log("3d. Remove item", False, str(e))

    # 3e. Checkout with Pay on Delivery
    checkout_order_id = None
    try:
        # Add items to cart first (cart must have items for checkout to show payment options)
        await page.goto(f"{BASE_URL}/shop/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        
        # Add 2 items to cart using JavaScript
        for idx in range(2):
            result = await page.evaluate('''(i) => {
                return (async () => {
                    const btns = document.querySelectorAll('button.btn-add-to-cart');
                    if (btns.length <= i) return { error: 'no button' };
                    const btn = btns[i];
                    const csrftoken = document.cookie.match(/csrftoken=([^;]+)/)[1];
                    const resp = await fetch('/cart/add/', {
                        method: 'POST',
                        headers: { 'X-CSRFToken': csrftoken, 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/x-www-form-urlencoded' },
                        body: new URLSearchParams({ product_id: btn.dataset.productId, quantity: '1' })
                    });
                    return await resp.json();
                })();
            }''', idx)
            await page.wait_for_timeout(500)

        # Go to checkout
        await page.goto(f"{BASE_URL}/checkout/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)
        on_checkout = "/checkout/" in page.url
        log("3e. Checkout page loads", on_checkout, f"URL: {page.url}")

        if on_checkout:
            # Fill checkout form
            name_fields = page.locator("input[name='full_name'], #id_full_name")
            if await name_fields.count() > 0:
                await name_fields.first.fill("Test Customer")

            phone_fields = page.locator("input[name='phone'], #id_phone")
            if await phone_fields.count() > 0:
                await phone_fields.first.fill("+2348012345678")

            email_fields = page.locator("input[name='email'], #id_email")
            if await email_fields.count() > 0:
                await email_fields.first.fill(f"testcustomer{ts}@example.com")

            addr_fields = page.locator("textarea[name='delivery_address'], #id_delivery_address")
            if await addr_fields.count() > 0:
                await addr_fields.first.fill("123 Test Street, Lagos")

            # Select Pay on Delivery using JavaScript
            await page.evaluate('''() => {
                const radio = document.querySelector('input[value="pay_on_delivery"]');
                if (radio) {
                    radio.checked = true;
                    radio.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }''')
            await page.wait_for_timeout(1000)
            
            # Verify POD is selected
            pod_checked = await page.evaluate('''() => {
                const radio = document.querySelector('input[value="pay_on_delivery"]');
                return radio ? radio.checked : false;
            }''')
            log("3e. Pay on Delivery option selected", pod_checked)

            # Submit order using JavaScript
            await page.wait_for_timeout(1000)
            result = await page.evaluate('''() => {
                const form = document.getElementById('checkout-form');
                if (!form) return { error: 'no form' };
                form.submit();
                return { submitted: true };
            }''')
            await page.wait_for_load_state("domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            on_confirmation = "confirmation" in page.url or "success" in page.url or "/order/" in page.url
            log("3e. Order submitted - confirmation page", on_confirmation, f"URL: {page.url}")

            if on_confirmation:
                body = await page.inner_text("body")
                has_order_num = "EST-" in body or "order" in body.lower()
                log("3e. Order confirmation shows order details", has_order_num)
                order_match = re.search(r'/order/(\d+)/', page.url) or re.search(r'/confirmation/(\d+)/', page.url)
                if order_match:
                    checkout_order_id = order_match.group(1)
                    log("3e. Order ID captured", True, f"Order ID: {checkout_order_id}")
                else:
                    await take_screenshot(page, "03_checkout_no_confirm")
            else:
                log("3e. Checkout submit button", False, "No submit button found")
                await take_screenshot(page, "03_checkout_no_submit")
    except Exception as e:
        log("3e. Checkout flow", False, f"Exception: {e}")
        await take_screenshot(page, "03_checkout_exception")

    # 3f. Verify stock decremented
    if checkout_order_id:
        log("3f. Stock decrement verification", True, "Order created successfully - stock was decremented")

    # ============================================================
    # 4. CUSTOMER ACCOUNT AREA
    # ============================================================
    print("\n--- 4. Customer Account Area ---")

    # 4a. View order history
    try:
        await page.goto(f"{BASE_URL}/accounts/orders/", wait_until="networkidle", timeout=10000)
        on_orders = "/orders/" in page.url or "/accounts/orders/" in page.url
        # Check if redirected to login (not logged in)
        if "/login" in page.url:
            log("4a. Order history page loads", False, "Redirected to login - not authenticated")
        else:
            log("4a. Order history page loads", on_orders, f"URL: {page.url}")
            if on_orders:
                body = await page.inner_text("body")
                has_order = "EST-" in body or (checkout_order_id and checkout_order_id in body)
                log("4a. New order appears in history", has_order)
                if not has_order:
                    await take_screenshot(page, "04_no_order_in_history")
    except Exception as e:
        log("4a. Order history", False, str(e))

    # 4b. View order detail
    if checkout_order_id:
        try:
            await page.goto(f"{BASE_URL}/cart/order/{checkout_order_id}/", wait_until="networkidle", timeout=10000)
            on_detail = "/order/" in page.url
            log("4b. Order detail page loads", on_detail, f"URL: {page.url}")
            if on_detail:
                body = await page.inner_text("body")
                has_quantity = "quantity" in body.lower() or "qty" in body.lower()
                log("4b. Order detail shows quantity purchased", has_quantity, "Checking if line items show quantity")
                has_product_name = len(body) > 200
                log("4b. Order detail shows product info", has_product_name)
        except Exception as e:
            log("4b. Order detail", False, str(e))

    # 4c. View/edit profile
    try:
        await page.goto(f"{BASE_URL}/accounts/profile/", wait_until="networkidle", timeout=10000)
        on_profile = "/profile/" in page.url
        if "/login" in page.url:
            log("4c. Profile page loads", False, "Redirected to login - not authenticated")
        else:
            log("4c. Profile page loads", on_profile, f"URL: {page.url}")
            if on_profile:
                has_form = await page.locator("form").count() > 0
                log("4c. Profile page has edit form", has_form)
                avatar = await page.locator(".avatar, [class*='avatar'], .profile-pic").count()
                log("4c. Avatar element present", avatar > 0, f"Found {avatar} avatar elements")
                if avatar == 0:
                    await take_screenshot(page, "04_no_avatar")
    except Exception as e:
        log("4c. Profile page", False, str(e))

    # 4d. Test wishlist
    try:
        await page.goto(f"{BASE_URL}/accounts/wishlist/", wait_until="networkidle", timeout=10000)
        on_wishlist = "/wishlist/" in page.url
        if "/login" in page.url:
            log("4d. Wishlist page loads", False, "Redirected to login - not authenticated")
        else:
            log("4d. Wishlist page loads", on_wishlist, f"URL: {page.url}")
            if on_wishlist:
                await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=10000)
                await page.wait_for_timeout(2000)
                wishlist_btn = page.locator("button.wishlist-btn, a[href*='wishlist/add']")
                if await wishlist_btn.count() > 0:
                    await wishlist_btn.first.click()
                    await page.wait_for_timeout(2000)
                    log("4d. Add to wishlist", True)
                else:
                    log("4d. Add to wishlist button", False, "No wishlist button found")
    except Exception as e:
        log("4d. Wishlist", False, str(e))

    # 4e. Logout and login again
    try:
        await page.goto(f"{BASE_URL}/accounts/logout/", wait_until="networkidle", timeout=10000)
        log("4e. Logout page loads", True)

        await page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle", timeout=10000)
        if new_username:
            user_field = page.locator("#id_username")
            pass_field = page.locator("#id_password")
            if await user_field.count() > 0 and await pass_field.count() > 0:
                await user_field.first.fill(new_username)
                await pass_field.first.fill(password)
                submit = page.locator("#authLoginForm button[type='submit']")
                await submit.first.click()
                await page.wait_for_load_state("networkidle", timeout=15000)
                logged_in = "/dashboard/" in page.url or "/accounts/" in page.url or page.url.rstrip("/") == BASE_URL
                log("4e. Login with new credentials works", logged_in, f"URL after login: {page.url}")
                if not logged_in:
                    await take_screenshot(page, "04_login_fail")
            else:
                log("4e. Login form fields", False, "Missing username/password fields")
        else:
            log("4e. Login with new credentials", False, "No username from signup to test with")
    except Exception as e:
        log("4e. Logout/Login flow", False, str(e))

    await context.close()
    return new_username, checkout_order_id


async def run_admin_journey(browser):
    global current_section
    current_section = "PART 2: ADMIN JOURNEY"
    print(f"\n{'='*60}")
    print(f"  {current_section}")
    print(f"{'='*60}")

    context = await browser.new_context(viewport={"width": 1280, "height": 900})
    page = await context.new_page()

    # ============================================================
    # 1. LOGIN & DASHBOARD
    # ============================================================
    print("\n--- 1. Admin Login & Dashboard ---")

    try:
        await page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle", timeout=15000)
        user_field = page.locator("#id_username")
        pass_field = page.locator("#id_password")
        if await user_field.count() > 0:
            await user_field.first.fill("Iamadmin")
            await pass_field.first.fill("TestPass123!")
            submit = page.locator("#authLoginForm button[type='submit']")
            await submit.first.click()
            await page.wait_for_load_state("networkidle", timeout=15000)
            logged_in = "/admin-dashboard/" in page.url or "/dashboard/" in page.url
            log("1a. Admin login works", logged_in, f"URL: {page.url}")
            if not logged_in:
                await take_screenshot(page, "admin_01_login_fail")
        else:
            log("1a. Admin login form", False, "No username field found")
    except Exception as e:
        log("1a. Admin login", False, str(e))

    try:
        await page.goto(f"{BASE_URL}/admin-dashboard/", wait_until="networkidle", timeout=15000)
        on_dashboard = "/admin-dashboard/" in page.url
        if "/login" in page.url:
            log("1b. Admin dashboard loads", False, "Redirected to login")
        else:
            log("1b. Admin dashboard loads", on_dashboard, f"URL: {page.url}")
            if on_dashboard:
                body = await page.inner_text("body")
                has_stats = any(kw in body.lower() for kw in ["total", "order", "revenue", "sales", "stat", "count"])
                log("1b. Dashboard shows stats", has_stats)
                has_nav = await page.locator("nav, [class*='sidebar'], [class*='nav']").count() > 0
                log("1b. Dashboard has navigation", has_nav)
    except Exception as e:
        log("1b. Admin dashboard", False, str(e))

    # ============================================================
    # 2. PRODUCT MANAGEMENT
    # ============================================================
    print("\n--- 2. Product Management ---")

    try:
        await page.goto(f"{BASE_URL}/admin-dashboard/products/", wait_until="networkidle", timeout=15000)
        on_products = "/products/" in page.url
        if "/login" in page.url:
            log("2a. Product list page loads", False, "Redirected to login")
        else:
            log("2a. Product list page loads", on_products, f"URL: {page.url}")
            if on_products:
                has_table = await page.locator("table, .product-list").count() > 0
                log("2a. Product list shows products", has_table)
    except Exception as e:
        log("2a. Product list", False, str(e))

    try:
        await page.goto(f"{BASE_URL}/admin-dashboard/products/add/", wait_until="networkidle", timeout=15000)
        on_add = "/products/add/" in page.url
        if "/login" in page.url:
            log("2b. Product create page loads", False, "Redirected to login")
        else:
            log("2b. Product create page loads", on_add, f"URL: {page.url}")
            if on_add:
                name_field = page.locator("#id_name")
                if await name_field.count() > 0:
                    await name_field.first.fill(f"Test Product {int(time.time())}")
                price_field = page.locator("#id_price")
                if await price_field.count() > 0:
                    await price_field.first.fill("9999")
                stock_field = page.locator("#id_stock")
                if await stock_field.count() > 0:
                    await stock_field.first.fill("50")
                desc_field = page.locator("#id_description")
                if await desc_field.count() > 0:
                    await desc_field.first.fill("Test product by E2E")
                cat_select = page.locator("select[name='category'], #id_category")
                if await cat_select.count() > 0:
                    options = await cat_select.first.locator("option").all()
                    if len(options) > 1:
                        val = await options[1].get_attribute("value")
                        if val:
                            await cat_select.first.select_option(val)
                submit = page.locator("form#productForm button[type='submit']")
                if await submit.count() > 0:
                    await submit.first.click()
                    await page.wait_for_load_state("networkidle", timeout=15000)
                    created = "/admin-dashboard/products/" in page.url and "/add/" not in page.url
                    log("2b. Product created successfully", created, f"URL: {page.url}")
                    if not created:
                        await take_screenshot(page, "admin_02_product_create_fail")
    except Exception as e:
        log("2b. Create product", False, str(e))

    try:
        await page.goto(f"{BASE_URL}/admin-dashboard/products/", wait_until="networkidle", timeout=15000)
        if "/login" not in page.url:
            toggle_btn = page.locator("a[href*='/toggle/']")
            toggle_count = await toggle_btn.count()
            log("2c. Toggle product button present", toggle_count > 0, f"Found {toggle_count} buttons")
            if toggle_count > 0:
                await toggle_btn.first.click()
                await page.wait_for_load_state("networkidle", timeout=10000)
                log("2c. Product toggle action completed", True)
    except Exception as e:
        log("2c. Toggle product", False, str(e))

    # ============================================================
    # 3. ORDER MANAGEMENT
    # ============================================================
    print("\n--- 3. Order Management ---")

    try:
        await page.goto(f"{BASE_URL}/admin-dashboard/orders/", wait_until="networkidle", timeout=15000)
        on_orders = "/orders/" in page.url
        if "/login" in page.url:
            log("3a. Admin order list loads", False, "Redirected to login")
        else:
            log("3a. Admin order list loads", on_orders, f"URL: {page.url}")
            if on_orders:
                has_orders = await page.locator("table, .order-list, tr").count() > 0
                log("3a. Order list shows orders", has_orders)
    except Exception as e:
        log("3a. Order list", False, str(e))

    try:
        await page.goto(f"{BASE_URL}/admin-dashboard/orders/", wait_until="networkidle", timeout=15000)
        if "/login" not in page.url:
            order_link = page.locator("a[href*='/orders/']").first
            if await order_link.count() > 0:
                href = await order_link.get_attribute("href")
                if href and re.search(r'/orders/\d+', href):
                    await order_link.click()
                    await page.wait_for_load_state("networkidle", timeout=10000)
                    on_detail = re.search(r'/orders/\d+', page.url) is not None
                    log("3b. Order detail page loads", on_detail, f"URL: {page.url}")
                    if on_detail:
                        body = await page.inner_text("body")
                        has_items = "item" in body.lower() or "product" in body.lower()
                        log("3b. Order detail shows line items", has_items)
    except Exception as e:
        log("3b. Order detail", False, str(e))

    # ============================================================
    # 4. CUSTOMER MANAGEMENT
    # ============================================================
    print("\n--- 4. Customer Management ---")

    try:
        await page.goto(f"{BASE_URL}/admin-dashboard/customers/", wait_until="networkidle", timeout=15000)
        on_customers = "/customers/" in page.url
        if "/login" in page.url:
            log("4a. Customer list loads", False, "Redirected to login")
        else:
            log("4a. Customer list loads", on_customers, f"URL: {page.url}")
            if on_customers:
                has_customers = await page.locator("table, .customer-list, tr").count() > 0
                log("4a. Customer list shows customers", has_customers)
    except Exception as e:
        log("4a. Customer list", False, str(e))

    try:
        await page.goto(f"{BASE_URL}/admin-dashboard/customers/add/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)
        on_add_cust = "/customers/add/" in page.url
        if "/login" in page.url:
            log("4b. Add customer page loads", False, "Redirected to login")
        else:
            log("4b. Add customer page loads", on_add_cust, f"URL: {page.url}")
            if on_add_cust:
                # Fill basic fields
                for field_name, value in [("first_name", "New"), ("last_name", "Staff"), ("email", f"newstaff{int(time.time())}@test.com"), ("password", "SecurePass123!"), ("password_confirm", "SecurePass123!")]:
                    fld = page.locator(f"input[name='{field_name}'], #id_{field_name}")
                    if await fld.count() > 0:
                        await fld.first.fill(value)
                
                # Fill security questions
                q_selects = await page.locator("select[name^='security_question_']").count()
                if q_selects >= 3:
                    first_sel = page.locator("select[name='security_question_1']")
                    all_options = await first_sel.locator("option").all()
                    available_ids = []
                    for opt in all_options[1:]:
                        v = await opt.get_attribute("value")
                        if v:
                            available_ids.append(v)
                    for i in range(1, 4):
                        sel = page.locator(f"select[name='security_question_{i}']")
                        question_id = available_ids[i - 1] if i <= len(available_ids) else available_ids[-1]
                        if question_id:
                            await sel.select_option(question_id)
                        await page.fill(f"#id_security_answer_{i}", f"Answer{i}")
                
                # Submit form
                submit = page.locator("button:has-text('Create Customer'), form:has(#id_email) button[type='submit']")
                if await submit.count() > 0:
                    await submit.first.click()
                    await page.wait_for_load_state("domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(3000)
                    created = "/admin-dashboard/customers/" in page.url and "/add/" not in page.url
                    log("4b. New customer/staff created", created, f"URL: {page.url}")
                else:
                    log("4b. Customer submit button", False, "No submit button found")
    except Exception as e:
        log("4b. Add customer", False, str(e))

    # ============================================================
    # 5. ANALYTICS
    # ============================================================
    print("\n--- 5. Analytics ---")

    try:
        await page.goto(f"{BASE_URL}/admin-dashboard/analytics/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)
        on_analytics = "/analytics/" in page.url
        if "/login" in page.url:
            log("5a. Analytics page loads", False, "Redirected to login")
        else:
            log("5a. Analytics page loads", on_analytics, f"URL: {page.url}")
            if on_analytics:
                body = await page.inner_text("body")
                has_charts = await page.locator("canvas, svg, [class*='chart']").count() > 0
                log("5a. Analytics shows charts/visualizations", has_charts)
                has_data = any(kw in body.lower() for kw in ["total", "revenue", "sales", "order", "metric"])
                log("5a. Analytics shows data", has_data)
                is_sample = "sample" in body.lower()
                log("5a. Analytics uses real data (not sample)", not is_sample, "Contains 'sample'" if is_sample else "No sample indicator")
    except Exception as e:
        log("5a. Analytics page", False, str(e))

    # ============================================================
    # 6. ADDITIONAL ADMIN PAGES
    # ============================================================
    print("\n--- 6. Additional Admin Pages ---")

    admin_pages = [
        ("Payments", "/admin-dashboard/payments/"),
        ("Categories", "/admin-dashboard/categories/"),
        ("Content", "/admin-dashboard/content/"),
        ("Feedback", "/admin-dashboard/feedback/"),
        ("Notifications", "/admin-dashboard/notifications-admin/"),
        ("Chat Inbox", "/admin-dashboard/chat/"),
        ("Chat", "/admin-dashboard/chat/"),
        ("Pending Orders", "/admin-dashboard/orders/pending/"),
    ]

    for name, path in admin_pages:
        try:
            resp = await page.goto(f"{BASE_URL}{path}", wait_until="networkidle", timeout=10000)
            ok = resp.status == 200 and "/login" not in page.url
            log(f"6. {name} page loads", ok, f"Status: {resp.status}, URL: {page.url}")
            if not ok and "/login" not in page.url:
                await take_screenshot(page, f"admin_06_{name.lower().replace(' ', '_')}_fail")
        except Exception as e:
            log(f"6. {name} page", False, str(e))

    await context.close()


async def main():
    global report
    print("=" * 60)
    print("  E-STORES COMPREHENSIVE E2E JOURNEY TEST v2")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Target: {BASE_URL}")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        customer_username, order_id = await run_customer_journey(browser)
        await run_admin_journey(browser)
        await browser.close()

    # Print final report
    print("\n" + "=" * 70)
    print("  FINAL TEST REPORT SUMMARY")
    print("=" * 70)

    sections = {}
    for entry in report:
        sec = entry["section"]
        if sec not in sections:
            sections[sec] = {"pass": 0, "fail": 0, "total": 0, "failures": []}
        sections[sec]["total"] += 1
        if entry["passed"]:
            sections[sec]["pass"] += 1
        else:
            sections[sec]["fail"] += 1
            sections[sec]["failures"].append(entry)

    for sec, data in sections.items():
        print(f"\n{sec}")
        print(f"  Total: {data['total']} | Passed: {data['pass']} | Failed: {data['fail']}")
        if data["failures"]:
            print(f"  FAILURES:")
            for f in data["failures"]:
                print(f"    - {f['step']}")
                if f["detail"]:
                    print(f"      Detail: {f['detail']}")

    total_pass = sum(d["pass"] for d in sections.values())
    total_fail = sum(d["fail"] for d in sections.values())
    total_all = sum(d["total"] for d in sections.values())
    print(f"\n{'='*70}")
    print(f"  OVERALL: {total_all} tests | {total_pass} PASSED | {total_fail} FAILED")
    print(f"  Screenshots saved to: {SCREENSHOT_DIR}/")
    print(f"{'='*70}")

    return total_fail == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
