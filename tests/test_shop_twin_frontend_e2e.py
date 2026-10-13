"""Playwright end-to-end test for Shop Twin frontend."""

import uuid
from pathlib import Path

import pytest
from playwright.async_api import async_playwright

from proofqa.contracts import WorldSpec
from proofqa.world import World

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"


@pytest.mark.asyncio
async def test_shop_twin_e2e_flow():
    """Verify register, search, add to cart, and checkout on the running Shop Twin."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    screenshot_path = RESULTS_DIR / "shop_twin_e2e.png"

    spec = WorldSpec(app="shop_twin", bugs=[], seed=999)
    world = World(spec)
    world.start()

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1280, "height": 800})
            page = await context.new_page()

            # 1. Navigate to home
            await page.goto(f"{world.url}/", wait_until="networkidle")
            title = await page.title()
            assert "ApexShop" in title

            # Verify product count exists
            product_count_el = page.locator('[data-testid="product-count"]')
            await product_count_el.wait_for()
            assert await product_count_el.is_visible()

            # 2. Register
            await page.click('button:has-text("Sign In")')
            await page.click('button:has-text("Sign up here")')
            unique_user = f"user_{uuid.uuid4().hex[:6]}"
            await page.fill('input[aria-label="Full Name"]', "E2E User")
            await page.fill('input[aria-label="Email Address"]', f"{unique_user}@example.com")
            await page.fill('input[aria-label="Password"]', "password123")
            await page.click('button[aria-label="Register"]')

            # Wait for products catalog to reappear
            await product_count_el.wait_for()

            # 3. Search
            await page.fill('input[aria-label="Search products"]', "Headphones")
            await page.click('button[aria-label="Submit Search"]')
            await page.wait_for_timeout(300)

            # 4. Add to cart
            add_btn = page.locator('button:has-text("Add to Cart")').first
            await add_btn.click()
            await page.wait_for_timeout(300)

            # Verify cart badge updated
            badge = page.locator('[data-testid="cart-badge"]')
            badge_text = await badge.text_content()
            assert badge_text and int(badge_text.strip()) >= 1

            # 5. Open Cart
            await page.click('button[aria-label="View Shopping Cart"]')
            cart_total = page.locator('[data-testid="cart-total"]')
            await cart_total.wait_for()
            assert await cart_total.is_visible()

            # 6. Proceed to Checkout
            await page.click('button[aria-label="Proceed to Checkout"]')
            await page.fill('textarea[aria-label="Shipping Address"]', "123 Automated Testing Way")
            await page.click('button[aria-label="Place Order"]')

            # 7. Verify Order History
            await page.wait_for_timeout(500)
            assert await page.locator('text=Order History').is_visible()

            # Save screenshot
            await page.screenshot(path=str(screenshot_path))
            assert screenshot_path.exists()

            await browser.close()
    finally:
        world.stop()
