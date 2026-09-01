"""Diagnostic script to inspect page HTML structure"""
import asyncio
import re
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # 1. Inspect shop page product links
        print("=" * 60)
        print("SHOP PAGE - Product links")
        print("=" * 60)
        await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=15000)
        links = await page.locator("a").all()
        product_links = []
        for link in links:
            href = await link.get_attribute("href") or ""
            if "/shop/" in href and href != "/shop/" and not href.endswith("/shop/"):
                text = await link.inner_text()
                if len(text) > 5:
                    product_links.append((href, text[:60]))
        print(f"Found {len(product_links)} product links:")
        for href, text in product_links[:5]:
            print(f"  {href} -> {text}")

        # 2. Inspect signup form
        print("\n" + "=" * 60)
        print("SIGNUP PAGE - Form structure")
        print("=" * 60)
        await page.goto(f"{BASE_URL}/accounts/signup/", wait_until="networkidle", timeout=15000)
        forms = await page.locator("form").all()
        print(f"Found {len(forms)} forms")
        for i, form in enumerate(forms):
            fid = await form.get_attribute("id") or "no-id"
            faction = await form.get_attribute("action") or "no-action"
            print(f"  Form {i}: id={fid}, action={faction}")
            buttons = await form.locator("button").all()
            for btn in buttons:
                btype = await btn.get_attribute("type") or "no-type"
                bid = await btn.get_attribute("id") or "no-id"
                btext = (await btn.inner_text())[:40]
                print(f"    Button: type={btype}, id={bid}, text={btext}")

        # 3. Inspect add-to-cart mechanism
        print("\n" + "=" * 60)
        print("PRODUCT DETAIL - Add to cart mechanism")
        print("=" * 60)
        # Go to first product
        if product_links:
            first_product_url = product_links[0][0]
            if not first_product_url.startswith("http"):
                first_product_url = BASE_URL + first_product_url
            await page.goto(first_product_url, wait_until="networkidle", timeout=15000)
            print(f"URL: {page.url}")
            # Look for add-to-cart forms or links
            cart_forms = await page.locator("form[action*='cart'], form[action*='add']").all()
            print(f"Cart forms: {len(cart_forms)}")
            for f in cart_forms:
                action = await f.get_attribute("action")
                print(f"  Form action: {action}")
            cart_links = await page.locator("a[href*='cart']").all()
            print(f"Cart links: {len(cart_links)}")
            for link in cart_links[:5]:
                href = await link.get_attribute("href")
                text = (await link.inner_text())[:30]
                print(f"  {href} -> {text}")
            # Check for buttons
            all_buttons = await page.locator("button").all()
            for btn in all_buttons:
                text = (await btn.inner_text())[:30]
                if "add" in text.lower() or "cart" in text.lower():
                    print(f"  Button: {text}")

        # 4. Inspect login form
        print("\n" + "=" * 60)
        print("LOGIN PAGE - Form structure")
        print("=" * 60)
        await page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle", timeout=15000)
        forms = await page.locator("form").all()
        for i, form in enumerate(forms):
            fid = await form.get_attribute("id") or "no-id"
            faction = await form.get_attribute("action") or "no-action"
            method = await form.get_attribute("method") or "no-method"
            print(f"  Form {i}: id={fid}, action={faction}, method={method}")
            buttons = await form.locator("button").all()
            for btn in buttons:
                btype = await btn.get_attribute("type") or "no-type"
                bid = await btn.get_attribute("id") or "no-id"
                btext = (await btn.inner_text())[:40]
                print(f"    Button: type={btype}, id={bid}, text={btext}")
            inputs = await form.locator("input").all()
            for inp in inputs:
                itype = await inp.get_attribute("type") or "no-type"
                iname = await inp.get_attribute("name") or "no-name"
                iid = await inp.get_attribute("id") or "no-id"
                print(f"    Input: type={itype}, name={iname}, id={iid}")

        # 5. Inspect checkout page
        print("\n" + "=" * 60)
        print("CHECKOUT PAGE - Structure")
        print("=" * 60)
        await page.goto(f"{BASE_URL}/checkout/", wait_until="networkidle", timeout=15000)
        print(f"URL: {page.url}")
        body = await page.inner_text("body")
        print(f"Body length: {len(body)}")
        if "empty" in body.lower():
            print("Cart is empty - checkout blocked")
        # Look for payment options
        radios = await page.locator("input[type='radio']").all()
        print(f"Radio buttons: {len(radios)}")
        for r in radios[:10]:
            val = await r.get_attribute("value") or "no-value"
            name = await r.get_attribute("name") or "no-name"
            rid = await r.get_attribute("id") or "no-id"
            print(f"  Radio: name={name}, value={val}, id={rid}")
        # Look for submit
        buttons = await page.locator("button[type='submit'], input[type='submit']").all()
        print(f"Submit buttons: {len(buttons)}")
        for btn in buttons:
            bid = await btn.get_attribute("id") or "no-id"
            btext = (await btn.inner_text())[:40]
            print(f"  Submit: id={bid}, text={btext}")

        await browser.close()

asyncio.run(main())
