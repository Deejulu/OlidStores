"""Investigate checkout submit and customer creation"""
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Login
        await page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle", timeout=15000)
        await page.fill("#id_username", "Iamadmin")
        await page.fill("#id_password", "TestPass123!")
        await page.locator("#authLoginForm button[type='submit']").click()
        await page.wait_for_load_state("networkidle", timeout=15000)

        # 1. Customer creation issue
        print("=" * 60)
        print("CUSTOMER CREATION INVESTIGATION")
        print("=" * 60)
        await page.goto(f"{BASE_URL}/admin-dashboard/customers/add/", wait_until="networkidle", timeout=15000)

        # Check form and submit button
        forms = await page.locator("form").all()
        print(f"Forms on page: {len(forms)}")
        for f in forms:
            fid = await f.get_attribute("id") or "no-id"
            faction = await f.get_attribute("action") or "no-action"
            fmethod = await f.get_attribute("method") or "no-method"
            print(f"  id={fid}, action={faction}, method={fmethod}")

        # Fill form
        email_field = page.locator("input[name='email'], #id_email")
        if await email_field.count() > 0:
            await email_field.first.fill(f"testcust{int(asyncio.get_event_loop().time())}@test.com")
        for field_name in ["first_name", "last_name"]:
            fld = page.locator(f"input[name='{field_name}'], #id_{field_name}")
            if await fld.count() > 0:
                await fld.first.fill("Test")
        pwd = page.locator("input[name='password'], #id_password")
        if await pwd.count() > 0:
            await pwd.first.fill("SecurePass123!")

        # Find the correct submit button
        submit = page.locator("form[action*='customers/add'] button[type='submit']")
        print(f"Submit buttons (correct form): {await submit.count()}")
        if await submit.count() == 0:
            # Try broader selector
            submit = page.locator("#add_customer_form button[type='submit'], form:has(#id_email) button[type='submit']")
            print(f"Submit buttons (broad): {await submit.count()}")

        # Check if there's a submit button with specific text
        buttons = await page.locator("button[type='submit']").all()
        for btn in buttons:
            text = (await btn.inner_text())[:40]
            bid = await btn.get_attribute("id") or "no-id"
            print(f"  Button: id={bid}, text={text}")

        # 2. Checkout submit button issue
        print("\n" + "=" * 60)
        print("CHECKOUT SUBMIT INVESTIGATION")
        print("=" * 60)

        # Add item and go to checkout
        await page.goto(f"{BASE_URL}/shop/", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)
        add_btn = page.locator("button.btn-add-to-cart").first
        if await add_btn.count() > 0:
            async with page.expect_response("**/cart/add/**", timeout=5000):
                await add_btn.click()
            await page.wait_for_timeout(1000)

        await page.goto(f"{BASE_URL}/checkout/", wait_until="networkidle", timeout=15000)

        # Select Pay on Delivery
        pod_label = page.locator("label[for='pod_method']")
        if await pod_label.count() > 0:
            await pod_label.first.click()
            print("Selected Pay on Delivery")

        # Check for submit button
        await page.wait_for_timeout(2000)
        submit_buttons = await page.locator("button[type='submit']").all()
        print(f"Submit buttons on checkout: {len(submit_buttons)}")
        for btn in submit_buttons:
            text = (await btn.inner_text())[:40]
            bid = await btn.get_attribute("id") or "no-id"
            visible = await btn.is_enabled()
            print(f"  Button: id={bid}, text={text}, enabled={visible}")

        # Check if the form has an ID
        forms = await page.locator("form").all()
        for f in forms:
            fid = await f.get_attribute("id") or "no-id"
            faction = await f.get_attribute("action") or "no-action"
            print(f"  Form: id={fid}, action={faction}")

        await browser.close()

asyncio.run(main())
