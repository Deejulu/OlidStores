"""Investigate signup and admin form issues"""
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # 1. Investigate signup form
        print("=" * 60)
        print("SIGNUP FORM INVESTIGATION")
        print("=" * 60)
        await page.goto(f"{BASE_URL}/accounts/signup/", wait_until="networkidle", timeout=15000)

        # Fill form
        await page.fill("#id_first_name", "Test")
        await page.fill("#id_last_name", "Customer")
        await page.fill("#id_password1", "SecurePass123!")
        await page.fill("#id_password2", "SecurePass123!")

        # Select security questions
        for i in range(1, 4):
            sel = page.locator(f"select[name='security_question_{i}']")
            options = await sel.locator("option").all()
            for opt in options[1:]:
                v = await opt.get_attribute("value")
                if v:
                    await sel.select_option(v)
                    break
            await page.fill(f"#id_security_answer_{i}", f"Answer{i}")

        # Check form action and method
        form_info = await page.evaluate("""
        (() => {
            const form = document.getElementById('signup-form');
            return {
                action: form.action,
                method: form.method,
                id: form.id
            };
        })()
        """)
        print(f"Form info: {form_info}")

        # Submit and capture response
        submit = page.locator("#signup-submit-button")
        print(f"Submit button: {await submit.count()}")

        # Monitor network
        responses = []
        async def on_resp(r):
            if "signup" in r.url.lower():
                try:
                    body = await r.text()
                except:
                    body = "ERROR"
                responses.append({"url": r.url, "status": r.status, "body": body[:200]})

        page.on("response", on_resp)

        await submit.click()
        await page.wait_for_load_state("networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        print(f"URL after submit: {page.url}")
        print(f"Responses: {len(responses)}")
        for r in responses:
            print(f"  {r['status']} {r['url'][:60]}: {r['body'][:100]}")

        # Check for form errors
        errors = await page.locator(".errorlist, .alert-danger, .form-error, .invalid-feedback").all_text_contents()
        print(f"Form errors: {errors}")

        # 2. Investigate admin product form
        print("\n" + "=" * 60)
        print("ADMIN PRODUCT FORM INVESTIGATION")
        print("=" * 60)

        # Login first
        await page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle", timeout=15000)
        await page.fill("#id_username", "Iamadmin")
        await page.fill("#id_password", "TestPass123!")
        await page.locator("#authLoginForm button[type='submit']").click()
        await page.wait_for_load_state("networkidle", timeout=15000)

        # Go to product add
        await page.goto(f"{BASE_URL}/admin-dashboard/products/add/", wait_until="networkidle", timeout=15000)

        # Check form action
        form_info = await page.evaluate("""
        (() => {
            const forms = document.querySelectorAll('form');
            let result = [];
            for (let f of forms) {
                result.push({action: f.action, method: f.method, id: f.id, class: f.className.substring(0, 50)});
            }
            return result;
        })()
        """)
        print(f"Forms on page: {form_info}")

        # Fill and submit
        name_field = page.locator("#id_name")
        if await name_field.count() > 0:
            await name_field.fill("Test Product")

        # Find submit button
        submit = page.locator("form button[type='submit']")
        print(f"Submit buttons: {await submit.count()}")

        if await submit.count() > 0:
            # Check what happens on click
            await submit.first.click()
            await page.wait_for_load_state("networkidle", timeout=15000)
            print(f"URL after submit: {page.url}")

        await browser.close()

asyncio.run(main())
