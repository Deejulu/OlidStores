"""Intercept add-to-cart with correct pattern"""
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Intercept ALL requests to find the pattern
        async def handle_route(route):
            url = route.request.url
            if "cart" in url.lower():
                print(f"ROUTE MATCHED: {route.request.method} {url}")
            await route.continue_()

        # Use a broader pattern
        await page.route("**/*cart*", handle_route)

        await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        # Verify the click handler is attached by checking if button has event listeners
        add_btn = page.locator("button.btn-add-to-cart").first
        print(f"Button count: {await add_btn.count()}")

        if await add_btn.count() > 0:
            # Check if the button is visible and enabled
            visible = await add_btn.is_visible()
            enabled = await add_btn.is_enabled()
            print(f"Button visible: {visible}, enabled: {enabled}")

            # Try clicking
            print("Clicking button...")
            await add_btn.click()
            await page.wait_for_timeout(3000)

        # Check badge
        badge = page.locator(".floating-cart .cart-count")
        text = await badge.inner_text() if await badge.count() > 0 else "NOT FOUND"
        print(f"\nCart badge text: {text}")

        # Also check if the button's onclick or dataset changed
        if await add_btn.count() > 0:
            disabled = await add_btn.get_attribute("disabled")
            print(f"Button disabled attr: {disabled}")

        await browser.close()

asyncio.run(main())
