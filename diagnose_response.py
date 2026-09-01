"""Check server response to add-to-cart"""
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        responses = []

        async def on_response(r):
            if "cart/add" in r.url.lower():
                try:
                    body = await r.json()
                except Exception as e:
                    body = f"JSON parse error: {e}, text: {await r.text()[:200]}"
                responses.append({"url": r.url, "status": r.status, "body": body})

        page.on("response", on_response)

        await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        add_btn = page.locator("button.btn-add-to-cart").first
        if await add_btn.count() > 0:
            await add_btn.click()
            await page.wait_for_timeout(3000)

        print(f"Responses captured: {len(responses)}")
        for r in responses:
            print(f"  Status: {r['status']}")
            print(f"  Body: {r['body']}")

        # Check badge
        badge = page.locator(".floating-cart .cart-count")
        text = await badge.inner_text() if await badge.count() > 0 else "NOT FOUND"
        print(f"\nCart badge: {text}")

        await browser.close()

asyncio.run(main())
