"""Add comprehensive error catching to the click handler"""
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Capture ALL console and errors
        all_messages = []

        def on_console(m):
            all_messages.append(f"[{m.type}] {m.text}")

        page.on("console", on_console)
        page.on("pageerror", lambda e: all_messages.append(f"[PAGEERROR] {e}"))

        await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        # Now let's manually test the click handler by dispatching a click
        # and watching what happens
        add_btn = page.locator("button.btn-add-to-cart").first
        if await add_btn.count() > 0:
            # First, let's see what happens when we call fetch directly from the handler
            # by simulating the exact same fetch call
            result = await page.evaluate("""
            (async () => {
                const csrftoken = getCookie('csrftoken');
                try {
                    const resp = await fetch('/cart/add/', {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': csrftoken,
                            'X-Requested-With': 'XMLHttpRequest',
                            'Content-Type': 'application/x-www-form-urlencoded'
                        },
                        body: new URLSearchParams({
                            product_id: '778',
                            quantity: '1'
                        })
                    });
                    const data = await resp.json();
                    return {success: true, data: data, cartCount: data.cart_count};
                } catch(e) {
                    return {success: false, error: e.message};
                }
            })()
            """)
            print(f"Direct fetch result: {result}")

            # Now click the button
            print("\nClicking button...")
            await add_btn.click()
            await page.wait_for_timeout(3000)

        # Print all messages
        print(f"\nAll console messages ({len(all_messages)}):")
        for msg in all_messages:
            if any(kw in msg.lower() for kw in ['cart', 'update', 'badge', 'null', 'error', 'response', 'success']):
                print(f"  {msg[:200]}")

        # Check badge
        badge = page.locator(".floating-cart .cart-count")
        text = await badge.inner_text() if await badge.count() > 0 else "NOT FOUND"
        print(f"\nCart badge: {text}")

        await browser.close()

asyncio.run(main())
