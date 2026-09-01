"""Check cart badge HTML structure"""
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

        # Get all elements with cart-count class
        badges = await page.locator(".cart-count").all()
        print(f"Elements with .cart-count: {len(badges)}")
        for b in badges:
            html = await b.evaluate("el => el.outerHTML")
            print(f"  HTML: {html[:200]}")
            parent = await b.evaluate("el => el.parentElement?.outerHTML?.substring(0, 200) || 'no parent'")
            print(f"  Parent: {parent}")
            print()

        # Check header structure
        print("=" * 60)
        print("HEADER CART LINK CHECK")
        print("=" * 60)
        header_cart = await page.locator('a[href="/cart/"]').all()
        print(f"a[href='/cart/'] elements: {len(header_cart)}")
        for el in header_cart:
            cls = await el.get_attribute("class") or "no-class"
            html = await el.evaluate("el => el.outerHTML")
            print(f"  class={cls}")
            print(f"  HTML: {html[:300]}")
            print()

        # Check notification-badge
        notif_badges = await page.locator(".notification-badge").all()
        print(f".notification-badge elements: {len(notif_badges)}")
        for b in notif_badges:
            html = await b.evaluate("el => el.outerHTML")
            print(f"  HTML: {html[:200]}")

        # Check floating-cart
        floating = await page.locator(".floating-cart").all()
        print(f"\n.floating-cart elements: {len(floating)}")
        for f in floating:
            html = await f.evaluate("el => el.outerHTML")
            print(f"  HTML: {html[:300]}")

        await browser.close()

asyncio.run(main())
