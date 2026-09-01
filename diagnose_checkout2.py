"""Debug checkout submission"""
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Capture console and network
        page.on("console", lambda m: print(f"[{m.type}] {m.text}"))
        page.on("pageerror", lambda e: print(f"[ERROR] {e}"))

        # Add item to cart
        await page.goto(f"{BASE_URL}/shop/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)
        
        add_btn = page.locator("button.btn-add-to-cart").first
        count = await add_btn.count()
        print(f"Add to cart buttons found: {count}")
        if count > 0:
            await add_btn.click()
            await page.wait_for_timeout(2000)
            print("Clicked add to cart")

        # Go to checkout
        await page.goto(f"{BASE_URL}/checkout/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)
        print(f"URL: {page.url}")

        # Fill all required fields
        fields_to_fill = {
            "input[name='full_name']": "Test Customer",
            "input[name='phone']": "+2348012345678",
            "input[name='email']": "test@example.com",
            "textarea[name='delivery_address']": "123 Test Street, Lagos",
        }
        for selector, value in fields_to_fill.items():
            fld = page.locator(selector)
            if await fld.count() > 0:
                await fld.first.fill(value)
                print(f"Filled {selector}")

        # Select delivery option
        del_2d = page.locator("input[value='2d']")
        if await del_2d.count() > 0:
            await del_2d.first.click()
            print("Selected 2d delivery")

        # Select Pay on Delivery
        print("Attempting to select Pay on Delivery...")
        try:
            # First, check what radio buttons exist
            radio_info = await page.evaluate("""
            (() => {
                const radios = document.querySelectorAll('input[name="payment_method"]');
                let info = [];
                for (let r of radios) {
                    info.push({ value: r.value, id: r.id, checked: r.checked, disabled: r.disabled });
                }
                return info;
            })()
            """)
            print(f"Radio buttons found: {radio_info}")

            # Try to check the radio button
            result = await page.evaluate("""
            (() => {
                const radio = document.querySelector('input[value="pay_on_delivery"]');
                if (radio) {
                    radio.checked = true;
                    radio.dispatchEvent(new Event('change', { bubbles: true }));
                    return { success: true, checked: radio.checked };
                }
                return { success: false, error: 'radio not found' };
            })()
            """)
            print(f"Radio check result: {result}")
        except Exception as e:
            print(f"Error: {e}")

        await page.wait_for_timeout(1000)

        # Verify which radio is checked
        radios = await page.locator("input[name='payment_method']").all()
        for r in radios:
            val = await r.get_attribute("value")
            checked = await r.is_checked()
            print(f"  Radio {val}: checked={checked}")

        # Check if manual-btn is now visible
        manual_btn = page.locator("#manual-btn")
        if await manual_btn.count() > 0:
            visible = await manual_btn.is_visible()
            print(f"manual-btn visible: {visible}")
            style = await manual_btn.get_attribute("style") or "no-style"
            print(f"manual-btn style: {style}")

        # Try clicking the visible submit button
        submit = page.locator("#manual-btn:visible, #paystack-btn:visible")
        print(f"Visible submit buttons: {await submit.count()}")

        # Check cart contents before submit
        cart_info = await page.evaluate("""
        (() => {
            const itemCount = document.querySelectorAll('.ck-item').length;
            const emptyMsg = document.querySelector('.text-center.py-5');
            return { itemCount: itemCount, hasEmptyMsg: !!emptyMsg };
        })()
        """)
        print(f"Cart info: {cart_info}")

        if await submit.count() > 0:
            print("Submitting form via JavaScript...")
            # Submit the form directly
            result = await page.evaluate("""
            (() => {
                const form = document.getElementById('checkout-form');
                if (form) {
                    const formData = new FormData(form);
                    return { action: form.action, method: form.method, data: Object.fromEntries(formData.entries()) };
                }
                return { error: 'form not found' };
            })()
            """)
            print(f"Form info: {result}")

            # Try direct form submission
            await page.evaluate("document.getElementById('checkout-form').submit()")
            await page.wait_for_load_state("networkidle", timeout=15000)
            print(f"URL after JS submit: {page.url}")

        await browser.close()

asyncio.run(main())
