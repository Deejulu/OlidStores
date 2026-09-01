"""Test add-to-cart endpoint directly"""
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Go to shop and capture console logs
        await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        # Listen for console messages and network
        console_msgs = []
        page.on("console", lambda m: console_msgs.append(f"{m.type}: {m.text}"))

        # Click add to cart
        add_btn = page.locator("button.btn-add-to-cart").first
        print(f"Add button found: {await add_btn.count()}")
        if await add_btn.count() > 0:
            product_id = await add_btn.get_attribute("data-product-id")
            print(f"Product ID: {product_id}")

            # Get CSRF token
            csrf = await page.evaluate("document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='))?.split('=')[1]") 
            print(f"CSRF token: {csrf}")

            # Click and wait
            await add_btn.click()
            await page.wait_for_timeout(3000)

            # Check console
            print(f"\nConsole messages ({len(console_msgs)}):")
            for msg in console_msgs[-10:]:
                print(f"  {msg}")

            # Check cart count elements
            badges = await page.locator("[class*='cart-count'], [class*='cart-badge'], .cart-total, #cart-count").all()
            print(f"\nCart badge elements: {len(badges)}")
            for b in badges:
                text = await b.inner_text()
                cls = await b.get_attribute("class")
                print(f"  class={cls}, text={text}")

        # Also test the endpoint directly via fetch
        print("\n" + "=" * 60)
        print("DIRECT ENDPOINT TEST")
        print("=" * 60)
        result = await page.evaluate("""
        async () => {
            const csrf = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='))?.split('=')[1];
            const resp = await fetch('/cart/add/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrf,
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: 'product_id=778&quantity=1'
            });
            const data = await resp.json();
            return { status: resp.status, data: data };
        }
        """)
        print(f"Direct fetch result: {result}")

        await browser.close()

asyncio.run(main())
