"""Detailed network monitoring for add-to-cart"""
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Monitor ALL network requests
        requests = []
        responses = []

        async def on_request(r):
            if "cart" in r.url.lower():
                requests.append({"url": r.url, "method": r.method, "headers": r.headers})

        async def on_response(r):
            if "cart" in r.url.lower():
                try:
                    body = await r.json()
                except:
                    body = await r.text() if r.status == 200 else None
                responses.append({"url": r.url, "status": r.status, "body": body})

        page.on("request", on_request)
        page.on("response", on_response)

        await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        # Click add to cart
        add_btn = page.locator("button.btn-add-to-cart").first
        print(f"Button found: {await add_btn.count()}")
        if await add_btn.count() > 0:
            print("Clicking...")
            await add_btn.click()
            await page.wait_for_timeout(4000)

        print(f"\nCart requests: {len(requests)}")
        for r in requests:
            print(f"  {r['method']} {r['url']}")

        print(f"\nCart responses: {len(responses)}")
        for r in responses:
            print(f"  Status {r['status']}: {r['body']}")

        # Check badge
        badge = page.locator(".floating-cart .cart-count")
        text = await badge.inner_text() if await badge.count() > 0 else "NOT FOUND"
        print(f"\nCart badge text: {text}")

        await browser.close()

asyncio.run(main())
