"""Intercept add-to-cart response"""
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Intercept the response
        async def handle_route(route):
            response = await route.fetch()
            body = await response.text()
            print(f"INTERCEPTED RESPONSE: status={response.status}, body={body[:500]}")
            await route.fulfill(response=response)

        await page.route("/cart/add/**", handle_route)

        await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        # Click add to cart
        add_btn = page.locator("button.btn-add-to-cart").first
        if await add_btn.count() > 0:
            await add_btn.click()
            await page.wait_for_timeout(3000)

        # Check badge
        badge = page.locator(".floating-cart .cart-count")
        text = await badge.inner_text() if await badge.count() > 0 else "NOT FOUND"
        print(f"\nCart badge text: {text}")

        await browser.close()

asyncio.run(main())
