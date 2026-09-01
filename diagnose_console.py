"""Capture ALL console messages and check for multiple handlers"""
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Capture ALL console messages
        all_console = []

        def on_console(m):
            all_console.append(f"{m.type}: {m.text}")

        page.on("console", on_console)

        await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        add_btn = page.locator("button.btn-add-to-cart").first
        if await add_btn.count() > 0:
            await add_btn.click()
            await page.wait_for_timeout(3000)

        # Filter for relevant messages
        print("Relevant console messages:")
        for msg in all_console:
            if any(kw in msg.lower() for kw in ['cart', 'update', 'badge', 'null', 'undefined', 'response']):
                print(f"  {msg[:150]}")

        # Check how many click listeners are on the button
        listener_count = await add_btn.evaluate("""
        (el => {
            // This doesn't work in standard browsers, but let's check
            return 'checking';
        })()
        """)

        # Alternative: check if there are multiple forms of the click handler
        script_tags = await page.locator("script").all()
        handler_count = 0
        for tag in script_tags:
            content = await tag.inner_text() or ""
            if "btn-add-to-cart" in content:
                handler_count += 1
        print(f"\nScript tags with btn-add-to-cart handler: {handler_count}")

        await browser.close()

asyncio.run(main())
