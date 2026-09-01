"""Test updateCartBadges directly"""
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

        # Test calling updateCartBadges directly
        result = await page.evaluate("""
        (() => {
            if (typeof window.updateCartBadges === 'function') {
                try {
                    window.updateCartBadges(5);
                    const badge = document.querySelector('.floating-cart .cart-count');
                    return {success: true, badgeText: badge ? badge.textContent : 'NOT FOUND', badgeDisplay: badge ? badge.display : 'N/A'};
                } catch(e) {
                    return {success: false, error: e.message};
                }
            } else {
                return {success: false, error: 'updateCartBadges not a function'};
            }
        })()
        """)
        print(f"Direct updateCartBadges(5): {result}")

        # Now test the actual click flow with console logging
        await page.evaluate("""
        window._clickLog = [];
        const origUpdate = window.updateCartBadges;
        window.updateCartBadges = function(count) {
            window._clickLog.push('updateCartBadges called with: ' + count);
            return origUpdate.call(this, count);
        };
        """)

        add_btn = page.locator("button.btn-add-to-cart").first
        if await add_btn.count() > 0:
            await add_btn.click()
            await page.wait_for_timeout(3000)

        click_log = await page.evaluate("window._clickLog")
        print(f"\nClick log: {click_log}")

        # Check badge
        badge = page.locator(".floating-cart .cart-count")
        text = await badge.inner_text() if await badge.count() > 0 else "NOT FOUND"
        print(f"Cart badge: {text}")

        await browser.close()

asyncio.run(main())
