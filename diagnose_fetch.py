"""Inject logging into the fetch response handler"""
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

        # Inject a script to intercept fetch and log
        await page.evaluate("""
        window._fetchLog = [];
        const origFetch = window.fetch;
        window.fetch = function(...args) {
            window._fetchLog.push({url: typeof args[0] === 'string' ? args[0] : args[0]?.url, method: args[1] && args[1].method || 'GET', body: args[1] && args[1].body || null, time: Date.now()});
            return origFetch.apply(this, args).then(resp => {
                const clone = resp.clone();
                clone.text().then(t => {
                    window._fetchLog[window._fetchLog.length - 1].responseStatus = resp.status;
                    window._fetchLog[window._fetchLog.length - 1].responseBody = t.substring(0, 500);
                });
                return resp;
            });
        };
        """)

        # Click add to cart
        add_btn = page.locator("button.btn-add-to-cart").first
        if await add_btn.count() > 0:
            await add_btn.click()
            await page.wait_for_timeout(3000)

        # Get the fetch log
        fetch_log = await page.evaluate("window._fetchLog")
        print(f"Fetch log entries: {len(fetch_log)}")
        for entry in fetch_log:
            if "cart" in str(entry.get("url", "")).lower():
                print(f"\n  URL: {entry.get('url')}")
                print(f"  Method: {entry.get('method')}")
                print(f"  Body: {entry.get('body')}")
                print(f"  Response Status: {entry.get('responseStatus')}")
                print(f"  Response Body: {entry.get('responseBody')}")

        # Check badge
        badge = page.locator(".floating-cart .cart-count")
        text = await badge.inner_text() if await badge.count() > 0 else "NOT FOUND"
        print(f"\nCart badge: {text}")

        await browser.close()

asyncio.run(main())
