"""Diagnostic - get rendered product HTML after JS loads"""
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Wait for products to fully load
        await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=15000)
        # Wait for loading overlay to disappear
        try:
            await page.wait_for_selector("#productsLoadingOverlay", state="hidden", timeout=10000)
        except:
            pass
        await page.wait_for_timeout(2000)

        # Get the product grid HTML
        print("=" * 60)
        print("PRODUCT GRID CONTAINER")
        print("=" * 60)
        grid = await page.locator("#productsGrid, #product-grid, .products-grid, #productList").all()
        print(f"Grid elements: {len(grid)}")
        for g in grid:
            cls = await g.get_attribute("class") or "no-class"
            gid = await g.get_attribute("id") or "no-id"
            print(f"  class={cls}, id={gid}")

        # Get first actual product card
        print("\n" + "=" * 60)
        print("FIRST PRODUCT CARD (after JS load)")
        print("=" * 60)
        cards = await page.locator(".product-card").all()
        print(f"Product cards: {len(cards)}")
        if cards:
            html = await cards[0].evaluate("el => el.outerHTML")
            with open("product_card.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"Product card HTML saved to product_card.html ({len(html)} chars)")
            # Print just the structure
            print(f"Card tag: {await cards[0].evaluate('el => el.tagName')}")
            print(f"Card classes: {await cards[0].get_attribute('class')}")

        # Check add-to-cart mechanism
        print("\n" + "=" * 60)
        print("ADD TO CART - JS behavior")
        print("=" * 60)
        add_btn = page.locator("button.btn-add-to-cart").first
        if await add_btn.count() > 0:
            # Check for onclick or data attributes
            attrs = await add_btn.evaluate("el => Object.fromEntries([...el.attributes].map(a => [a.name, a.value]))")
            for k,v in attrs.items():
                print(f"  {k}={v}")

        # Try clicking and watch network
        print("\n" + "=" * 60)
        print("ADD TO CART - Network request test")
        print("=" * 60)
        # Listen for network requests
        requests = []
        page.on("request", lambda r: requests.append(r.url) if "cart" in r.url.lower() else None)
        if await add_btn.count() > 0:
            await add_btn.click()
            await page.wait_for_timeout(3000)
            print(f"Cart-related requests: {requests}")
            # Check cart count again
            cart_count = await page.locator("[class*='cart-count'], [class*='cart-badge'], .cart-total").all_text_contents()
            print(f"Cart count after: {cart_count}")

        await browser.close()

asyncio.run(main())
