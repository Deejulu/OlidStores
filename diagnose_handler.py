"""Debug the click handler"""
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(3000)

        # Add a click listener that logs BEFORE the existing handler
        await page.evaluate("""
        document.addEventListener('click', function(e) {
            const btn = e.target.closest('.btn-add-to-cart');
            if (btn) {
                console.log('CLICK HANDLER FIRED! productId:', btn.dataset.productId);
            }
        }, true);  // capture phase - fires first
        """)

        # Also listen for the cart/add response
        await page.evaluate("""
        window._cartResponse = null;
        const origFetch = window.fetch;
        window.fetch = function(...args) {
            return origFetch.apply(this, args).then(resp => {
                const clone = resp.clone();
                clone.text().then(t => {
                    if (typeof args[0] === 'string' && args[0].includes('cart/add')) {
                        window._cartResponse = {status: resp.status, body: t};
                    }
                });
                return resp;
            });
        };
        """)

        # Click button
        add_btn = page.locator("button.btn-add-to-cart").first
        print(f"Button found: {await add_btn.count()}")
        if await add_btn.count() > 0:
            await add_btn.click()
            await page.wait_for_timeout(3000)

        # Check the response
        cart_resp = await page.evaluate("window._cartResponse")
        print(f"\nCart response: {cart_resp}")

        # Check badge
        badge = page.locator(".floating-cart .cart-count")
        text = await badge.inner_text() if await badge.count() > 0 else "NOT FOUND"
        print(f"Cart badge: {text}")

        await browser.close()

asyncio.run(main())
