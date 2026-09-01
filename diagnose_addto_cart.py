"""Debug add-to-cart"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Set up error logging
        page.on("pageerror", lambda e: print(f"[PAGE ERROR] {e}"))

        # Navigate to shop
        await page.goto('http://127.0.0.1:8000/shop/', wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(8000)

        # Check for JS errors
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        # Try add to cart - use first button
        add_btn = page.locator('button.btn-add-to-cart').first
        count = await add_btn.count()
        print(f'Add to cart buttons found: {count}')
        if count > 0:
            # Scroll to button and click
            await add_btn.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)
            await add_btn.click(force=True)
            await page.wait_for_timeout(3000)

            print(f'Page errors: {errors}')

            # Check cart count
            cart_count = await page.evaluate('''() => {
                const badges = document.querySelectorAll('.cart-badge, .floating-cart-badge');
                return Array.from(badges).map(b => b.textContent).join(', ');
            }''')
            print(f'Cart badges: {cart_count}')

        await browser.close()

asyncio.run(main())
