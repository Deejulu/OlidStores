"""Debug response handler"""
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        response_count = [0]

        async def on_response(r):
            response_count[0] += 1
            url = r.url
            if "cart" in url.lower() or response_count[0] <= 5:
                try:
                    text = await r.text()
                except:
                    text = "COULD NOT READ"
                print(f"RESPONSE #{response_count[0]}: {r.status} {url[:80]} body={text[:100]}")

        page.on("response", on_response)

        await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        print(f"\nTotal responses so far: {response_count[0]}")

        add_btn = page.locator("button.btn-add-to-cart").first
        if await add_btn.count() > 0:
            await add_btn.click()
            await page.wait_for_timeout(3000)

        print(f"Total responses after click: {response_count[0]}")

        await browser.close()

asyncio.run(main())
