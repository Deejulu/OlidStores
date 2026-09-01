"""Log the actual data object in the fetch handler"""
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

        # Inject a wrapper around fetch to log the response data
        await page.evaluate("""
        window._fetchDebug = [];
        const origFetch = window.fetch;
        window.fetch = function(...args) {
            const promise = origFetch.apply(this, args);
            const entry = {url: typeof args[0] === 'string' ? args[0] : args[0]?.url, time: Date.now()};
            window._fetchDebug.push(entry);
            return promise.then(resp => {
                const clone = resp.clone();
                return clone.json().then(data => {
                    entry.responseStatus = resp.status;
                    entry.responseData = data;
                    entry.cartCount = data?.cart_count;
                    return resp;
                }).catch(e => {
                    entry.jsonError = e.message;
                    return resp;
                });
            });
        };
        """)

        add_btn = page.locator("button.btn-add-to-cart").first
        if await add_btn.count() > 0:
            await add_btn.click()
            await page.wait_for_timeout(3000)

        debug = await page.evaluate("window._fetchDebug")
        print(f"Fetch debug entries: {len(debug)}")
        for entry in debug:
            if "cart" in str(entry.get("url", "")).lower():
                print(f"\n  URL: {entry.get('url')}")
                print(f"  Status: {entry.get('responseStatus')}")
                print(f"  Data: {entry.get('responseData')}")
                print(f"  Cart count: {entry.get('cartCount')}")
                print(f"  JSON error: {entry.get('jsonError')}")

        await browser.close()

asyncio.run(main())
