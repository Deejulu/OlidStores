"""Check for JS errors and getCookie function"""
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: print(f"CONSOLE {m.type}: {m.text}") if "cart" in m.text.lower() or "error" in m.text.lower() else None)

        await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        # Check if getCookie is defined
        has_getcookie = await page.evaluate("typeof getCookie === 'function'")
        print(f"getCookie function defined: {has_getcookie}")

        # Click add to cart
        add_btn = page.locator("button.btn-add-to-cart").first
        if await add_btn.count() > 0:
            print("Clicking add to cart...")
            await add_btn.click()
            await page.wait_for_timeout(3000)

        # Check errors
        print(f"\nPage errors: {len(errors)}")
        for e in errors:
            print(f"  ERROR: {e}")

        # Check cart badge
        badge = page.locator(".floating-cart .cart-count")
        if await badge.count() > 0:
            text = await badge.inner_text()
            display = await badge.evaluate("el => el.style.display")
            print(f"\nCart badge: text={text}, display={display}")

        await browser.close()

asyncio.run(main())
