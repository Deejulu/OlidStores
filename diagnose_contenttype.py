"""Check response Content-Type header"""
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        add_btn = page.locator("button.btn-add-to-cart").first
        if await add_btn.count() > 0:
            async with page.expect_response("**/cart/add/**", timeout=5000) as resp_info:
                await add_btn.click()
            resp = await resp_info.value
            print(f"Status: {resp.status}")
            print(f"ALL headers:")
            for k, v in resp.headers.items():
                print(f"  {k}: {v}")

        await browser.close()

asyncio.run(main())
