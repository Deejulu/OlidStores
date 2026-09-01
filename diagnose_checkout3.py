"""Debug checkout form submission"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        page.on('pageerror', lambda e: print(f'[ERROR] {e}'))

        # Add item to cart
        await page.goto('http://127.0.0.1:8000/shop/', wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(3000)

        await page.evaluate('''async () => {
            const btn = document.querySelector('button.btn-add-to-cart');
            const csrftoken = document.cookie.match(/csrftoken=([^;]+)/)[1];
            await fetch('/cart/add/', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrftoken, 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({ product_id: btn.dataset.productId, quantity: '1' })
            });
        }''')

        # Go to checkout
        await page.goto('http://127.0.0.1:8000/checkout/', wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(2000)

        # Fill form
        await page.fill('input[name="full_name"]', 'Test Customer')
        await page.fill('input[name="phone"]', '+2348012345678')
        await page.fill('input[name="email"]', 'test@example.com')
        await page.fill('textarea[name="delivery_address"]', '123 Test Street, Lagos')

        # Check if payment method radio buttons exist
        radio_info = await page.evaluate('''() => {
            const radios = document.querySelectorAll('input[name="payment_method"]');
            let info = [];
            for (let r of radios) {
                info.push({ value: r.value, id: r.id, checked: r.checked, disabled: r.disabled });
            }
            return info;
        }''')
        print(f'Radio buttons: {radio_info}')

        # Check form action
        form_info = await page.evaluate('''() => {
            const form = document.getElementById('checkout-form');
            if (!form) return { error: 'no form' };
            return { action: form.action, method: form.method };
        }''')
        print(f'Form info: {form_info}')

        # Select POD
        await page.evaluate('''() => {
            const radio = document.querySelector('input[value="pay_on_delivery"]');
            if (radio) {
                radio.checked = true;
                radio.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }''')
        await page.wait_for_timeout(1000)

        # Check if POD is checked
        pod_checked = await page.evaluate('''() => {
            const radio = document.querySelector('input[value="pay_on_delivery"]');
            return radio ? radio.checked : false;
        }''')
        print(f'POD checked: {pod_checked}')

        # Submit form
        await page.evaluate('document.getElementById("checkout-form").submit()')
        await page.wait_for_load_state('domcontentloaded', timeout=30000)
        await page.wait_for_timeout(3000)

        print(f'URL: {page.url}')

        # Check for errors
        errors = await page.locator('.alert, .errorlist, .text-danger').all_text_contents()
        print(f'Errors: {errors[:5]}')

        await browser.close()

asyncio.run(main())
