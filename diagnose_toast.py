"""Patch the click handler to catch errors"""
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

        await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        # Check if showCartToast is defined
        has_toast = await page.evaluate("typeof showCartToast === 'function'")
        print(f"showCartToast defined: {has_toast}")

        # Patch console.warn and console.error to capture
        await page.evaluate("""
        window._consoleErrors = [];
        const origError = console.error;
        console.error = function(...args) {
            window._consoleErrors.push(args.map(a => String(a)).join(' '));
            return origError.apply(this, args);
        };
        const origWarn = console.warn;
        console.warn = function(...args) {
            window._consoleErrors.push('WARN: ' + args.map(a => String(a)).join(' '));
            return origWarn.apply(this, args);
        };
        """)

        add_btn = page.locator("button.btn-add-to-cart").first
        if await add_btn.count() > 0:
            await add_btn.click()
            await page.wait_for_timeout(3000)

        console_errors = await page.evaluate("window._consoleErrors")
        print(f"\nConsole errors/warnings: {len(console_errors)}")
        for msg in console_errors[-10:]:
            print(f"  {msg[:150]}")

        print(f"\nPage errors: {len(errors)}")
        for e in errors:
            print(f"  {e[:150]}")

        # Check badge
        badge = page.locator(".floating-cart .cart-count")
        text = await badge.inner_text() if await badge.count() > 0 else "NOT FOUND"
        print(f"\nCart badge: {text}")

        await browser.close()

asyncio.run(main())
