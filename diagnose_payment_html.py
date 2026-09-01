"""Check payment options in HTML"""
import asyncio
import re
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto('http://127.0.0.1:8000/checkout/', wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(2000)

        html = await page.content()

        # Search for the payment options
        manual_match = re.search(r'enable_manual.{0,100}', html)
        pod_match = re.search(r'enable_pay_on_delivery.{0,100}', html)

        print(f'enable_manual in HTML: {manual_match.group() if manual_match else "NOT FOUND"}')
        print(f'enable_pay_on_delivery in HTML: {pod_match.group() if pod_match else "NOT FOUND"}')

        # Check for Bank Transfer or Pay on Delivery text
        has_bank = 'Bank Transfer' in html
        has_pod = 'Pay on Delivery' in html
        print(f'Has Bank Transfer text: {has_bank}')
        print(f'Has Pay on Delivery text: {has_pod}')

        await browser.close()

asyncio.run(main())
