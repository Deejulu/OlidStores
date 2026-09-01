"""Check actual POST body"""
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Intercept and log the POST body
        async def handle_route(route):
            if "cart/add" in route.request.url:
                post_data = route.request.post_data
                headers = route.request.headers
                print(f"INTERCEPTED /cart/add/")
                print(f"  Post data: {post_data}")
                print(f"  Content-Type: {headers.get('content-type')}")
                print(f"  X-Requested-With: {headers.get('x-requested-with')}")
            await route.continue_()

        await page.route("**/*cart/add*", handle_route)

        await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        add_btn = page.locator("button.btn-add-to-cart").first
        if await add_btn.count() > 0:
            await add_btn.click()
            await page.wait_for_timeout(3000)

        await browser.close()

asyncio.run(main())
