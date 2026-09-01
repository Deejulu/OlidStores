"""Check for 500 errors on add-to-cart"""
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Capture ALL responses with status
        all_responses = []

        async def on_response(r):
            try:
                text = await r.text()
            except:
                text = "ERROR READING"
            all_responses.append({"status": r.status, "url": r.url, "text": text[:150]})

        page.on("response", on_response)

        await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        add_btn = page.locator("button.btn-add-to-cart").first
        if await add_btn.count() > 0:
            await add_btn.click()
            await page.wait_for_timeout(4000)

        # Filter for cart/add responses
        cart_responses = [r for r in all_responses if "cart/add" in r["url"].lower() or "cart" in r["url"].lower()]
        print(f"Cart-related responses: {len(cart_responses)}")
        for r in cart_responses:
            print(f"  Status {r['status']}: {r['url'][:60]}")
            print(f"    Body: {r['text'][:100]}")

        # Also check for any 500 errors
        errors = [r for r in all_responses if r["status"] >= 400]
        print(f"\nError responses (4xx/5xx): {len(errors)}")
        for r in errors:
            print(f"  Status {r['status']}: {r['url'][:60]}")
            print(f"    Body: {r['text'][:100]}")

        await browser.close()

asyncio.run(main())
