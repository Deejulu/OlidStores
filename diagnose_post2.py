"""Capture POST data via request event"""
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        post_bodies = []

        def on_request(r):
            if r.method == "POST" and "cart" in r.url.lower():
                post_bodies.append({
                    "url": r.url,
                    "postData": r.post_data,
                    "headers": dict(r.headers)
                })

        page.on("request", on_request)

        await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        add_btn = page.locator("button.btn-add-to-cart").first
        if await add_btn.count() > 0:
            await add_btn.click()
            await page.wait_for_timeout(3000)

        print(f"POST bodies captured: {len(post_bodies)}")
        for pb in post_bodies:
            print(f"  URL: {pb['url']}")
            print(f"  Post data: {pb['postData']}")
            ct = pb['headers'].get('content-type', '')
            print(f"  Content-Type: {ct}")
            xrw = pb['headers'].get('x-requested-with', '')
            print(f"  X-Requested-With: {xrw}")

        await browser.close()

asyncio.run(main())
