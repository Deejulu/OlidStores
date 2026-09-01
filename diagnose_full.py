"""Full diagnostic - check what makes the POST and why handler fails"""
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Capture ALL requests with their initiators
        all_requests = []
        page.on("request", lambda r: all_requests.append({
            "url": r.url,
            "method": r.method,
            "resourceType": r.resource_type,
            "headers": r.headers
        }))

        await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(3000)

        print(f"Requests during page load: {len(all_requests)}")
        for r in all_requests:
            if "cart" in r["url"].lower():
                print(f"  CART: {r['method']} {r['url']} (type: {r['resourceType']})")

        # Clear and click
        all_requests.clear()

        add_btn = page.locator("button.btn-add-to-cart").first
        if await add_btn.count() > 0:
            # Check button type
            btn_type = await add_btn.get_attribute("type")
            print(f"\nButton type: {btn_type}")

            # Check if button is inside a form
            in_form = await add_btn.evaluate("el => el.closest('form') !== null")
            print(f"Button in form: {in_form}")

            # Check parent elements
            parent_info = await add_btn.evaluate("""el => {
                let p = el.parentElement;
                let chain = [];
                while (p && chain.length < 5) {
                    chain.push(p.tagName + '.' + (p.className||'').substring(0,50) + '#' + (p.id||''));
                    p = p.parentElement;
                }
                return chain;
            }""")
            print(f"Parent chain: {parent_info}")

            print("\nClicking button...")
            await add_btn.click()
            await page.wait_for_timeout(3000)

        print(f"\nRequests after click: {len(all_requests)}")
        for r in all_requests:
            print(f"  {r['method']} {r['url']} (type: {r['resourceType']})")
            if "cart" in r["url"].lower():
                print(f"    Headers: {dict(list(r['headers'].items())[:5])}")

        await browser.close()

asyncio.run(main())
