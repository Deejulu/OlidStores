"""Verify if button click triggers fetch"""
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Count ALL POST requests
        post_requests = []
        page.on("request", lambda r: post_requests.append(r.url) if r.method == "POST" else None)

        await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(3000)

        print(f"POST requests so far: {len(post_requests)}")
        for r in post_requests:
            print(f"  {r}")

        # Now click ONLY the button (no direct fetch)
        add_btn = page.locator("button.btn-add-to-cart").first
        print(f"\nButton count: {await add_btn.count()}")
        if await add_btn.count() > 0:
            print("Clicking button (no other actions)...")
            await add_btn.click()
            await page.wait_for_timeout(4000)

        print(f"\nPOST requests after click: {len(post_requests)}")
        for r in post_requests:
            print(f"  {r}")

        # Check badge
        badge = page.locator(".floating-cart .cart-count")
        text = await badge.inner_text() if await badge.count() > 0 else "NOT FOUND"
        print(f"\nCart badge: {text}")

        # Check if there was a page navigation
        print(f"Current URL: {page.url}")

        await browser.close()

asyncio.run(main())
