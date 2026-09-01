"""Deep diagnostic - inspect product cards and forms"""
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # 1. Get product card HTML structure
        print("=" * 60)
        print("PRODUCT CARD HTML")
        print("=" * 60)
        await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=15000)
        # Get first product card's outer HTML
        cards = await page.locator(".product-card, .product-item, [class*='product']").all()
        if cards:
            html = await cards[0].evaluate("el => el.outerHTML")
            print(html[:2000])

        # 2. Check how add-to-cart works
        print("\n" + "=" * 60)
        print("ADD TO CART - Button HTML")
        print("=" * 60)
        add_btns = await page.locator("button:has-text('Add to Cart')").all()
        if add_btns:
            html = await add_btns[0].evaluate("el => el.outerHTML")
            print(html[:1000])
            # Check if it's inside a form
            parent = await add_btns[0].evaluate("el => el.closest('form')?.outerHTML || 'NO FORM PARENT'")
            print(f"\nParent form: {parent[:500]}")

        # 3. Try clicking Add to Cart and see what happens
        print("\n" + "=" * 60)
        print("ADD TO CART - Click test")
        print("=" * 60)
        if add_btns:
            await add_btns[0].click()
            await page.wait_for_timeout(2000)
            print(f"URL after click: {page.url}")
            # Check for any response or redirect
            body = await page.inner_text("body")
            if "cart" in body.lower() and "added" in body.lower():
                print("Item was added to cart")
            # Check cart count in header
            cart_count = await page.locator("[class*='cart-count'], [class*='cart-badge'], .cart-total").all_text_contents()
            print(f"Cart count elements: {cart_count}")

        # 4. Navigate to product detail - try clicking product name/image
        print("\n" + "=" * 60)
        print("PRODUCT DETAIL NAVIGATION")
        print("=" * 60)
        await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=15000)
        # Try clicking on product name link
        name_links = await page.locator(".product-name a, .product-title a, h3 a, h2 a").all()
        print(f"Name links found: {len(name_links)}")
        if name_links:
            href = await name_links[0].get_attribute("href")
            print(f"First name link href: {href}")
            await name_links[0].click()
            await page.wait_for_load_state("networkidle", timeout=10000)
            print(f"URL after click: {page.url}")
        else:
            # Try clicking the product image
            images = await page.locator(".product-image img, .product-card img").all()
            print(f"Product images: {len(images)}")
            if images:
                # Check if image is wrapped in a link
                parent_link = await images[0].evaluate("el => el.closest('a')?.href || 'NO LINK'")
                print(f"Image parent link: {parent_link}")

        # 5. Check signup form - why did it fail?
        print("\n" + "=" * 60)
        print("SIGNUP FORM - Detailed check")
        print("=" * 60)
        await page.goto(f"{BASE_URL}/accounts/signup/", wait_until="networkidle", timeout=15000)
        # Check all inputs in signup form
        signup_form = page.locator("#signup-form")
        inputs = await signup_form.locator("input, select, textarea").all()
        for inp in inputs:
            itype = await inp.get_attribute("type") or "no-type"
            iname = await inp.get_attribute("name") or "no-name"
            iid = await inp.get_attribute("id") or "no-id"
            irequired = await inp.get_attribute("required")
            print(f"  Input: type={itype}, name={iname}, id={iid}, required={irequired}")

        await browser.close()

asyncio.run(main())
