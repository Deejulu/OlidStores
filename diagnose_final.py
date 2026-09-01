"""Check analytics timeout and checkout payment issue"""
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Login as admin
        await page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle", timeout=15000)
        await page.fill("#id_username", "Iamadmin")
        await page.fill("#id_password", "TestPass123!")
        await page.locator("#authLoginForm button[type='submit']").click()
        await page.wait_for_load_state("networkidle", timeout=15000)

        # Check analytics page with longer timeout
        print("=" * 60)
        print("ANALYTICS PAGE TEST")
        print("=" * 60)
        try:
            resp = await page.goto(f"{BASE_URL}/admin-dashboard/analytics/", wait_until="domcontentloaded", timeout=30000)
            print(f"Status: {resp.status}")
            print(f"URL: {page.url}")
            await page.wait_for_timeout(5000)
            body = await page.inner_text("body")
            print(f"Body length: {len(body)}")
            has_charts = await page.locator("canvas, svg").count()
            print(f"Charts found: {has_charts}")
        except Exception as e:
            print(f"Error: {e}")

        # Check checkout payment method
        print("\n" + "=" * 60)
        print("CHECKOUT PAYMENT METHOD TEST")
        print("=" * 60)

        # Add item to cart first
        await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)
        add_btn = page.locator("button.btn-add-to-cart").first
        if await add_btn.count() > 0:
            async with page.expect_response("**/cart/add/**", timeout=5000):
                await add_btn.click()
            await page.wait_for_timeout(1000)

        await page.goto(f"{BASE_URL}/checkout/", wait_until="networkidle", timeout=15000)
        print(f"Checkout URL: {page.url}")

        # Check payment method options
        payment_options = await page.locator("input[name='payment_method']").all()
        print(f"Payment method options: {len(payment_options)}")
        for opt in payment_options:
            val = await opt.get_attribute("value")
            label = await opt.evaluate("el => el.closest('label')?.textContent?.trim() || 'no label'")
            print(f"  Value: {val}, Label: {label}")

        # Check if payment-logo div is blocking
        logos = await page.locator(".payment-logo").all()
        print(f"\n.payment-logo elements: {len(logos)}")
        for logo in logos:
            style = await logo.get_attribute("style") or "no-style"
            parent = await logo.evaluate("el => el.parentElement?.tagName + '.' + (el.parentElement?.className||'').substring(0,50)")
            print(f"  Parent: {parent}, Style: {style}")

        # Try clicking the label instead of the input
        pod_label = page.locator("label[for='pod_method']")
        if await pod_label.count() > 0:
            print(f"\nFound label for pod_method")
            # Check if label is clickable
            box = await pod_label.bounding_box()
            print(f"Label bounding box: {box}")

        await browser.close()

asyncio.run(main())
