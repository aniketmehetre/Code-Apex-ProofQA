"""Acceptance tests for browser harness, perception, and prioritized execution."""

import pytest

from proofqa.browser import BrowserHarness, detect_volatile_regions, execute, get_page_fingerprint
from proofqa.contracts import Action, ActionKind, Locator, WorldSpec
from proofqa.world import World


@pytest.mark.asyncio
async def test_fingerprint_stability_with_d04_masking():
    """Verify page fingerprint is deterministic across fresh loads despite rotating decoy banner D04."""
    spec = WorldSpec(app="shop_twin", bugs=[], seed=42)

    with World(spec) as world:
        async with BrowserHarness() as harness:
            # Load 1
            ctx1, page1 = await harness.new_context()
            await page1.goto(world.url, wait_until="networkidle")
            raw_text1 = await page1.aria_snapshot()

            # Load 2
            ctx2, page2 = await harness.new_context()
            await page2.goto(world.url, wait_until="networkidle")
            raw_text2 = await page2.aria_snapshot()

            # Detect volatile region from difference (D04 rotating banner)
            volatile_mask = detect_volatile_regions(raw_text1, raw_text2)

            # Get fingerprints with mask applied
            fp1 = await get_page_fingerprint(page1, volatile_mask=volatile_mask)
            fp2 = await get_page_fingerprint(page2, volatile_mask=volatile_mask)

            assert fp1.url_path == fp2.url_path == "/"
            assert fp1.control_count == fp2.control_count
            assert fp1.aria_hash == fp2.aria_hash
            assert fp1.simhash == fp2.simhash

            await ctx1.close()
            await ctx2.close()


@pytest.mark.asyncio
async def test_execute_click_action():
    """Verify prioritized executor can resolve and click semantic elements."""
    spec = WorldSpec(app="shop_twin", bugs=[], seed=42)

    with World(spec) as world:
        async with BrowserHarness() as harness:
            ctx, page = await harness.new_context()
            await page.goto(world.url, wait_until="networkidle")

            # Click About button
            about_action = Action(
                id="act_about",
                kind=ActionKind.CLICK,
                locator=Locator(role="button", name="About"),
            )
            ok, reason = await execute(page, about_action, timeout_ms=3000)
            assert ok is True
            assert reason is None
            assert await page.locator("text=About ApexShop Twin").is_visible()

            await ctx.close()


@pytest.mark.asyncio
async def test_missing_element_returns_not_executable():
    """Verify unexecutable element returns not_executable with a clear reason feeding UNRESOLVED."""
    spec = WorldSpec(app="shop_twin", bugs=[], seed=42)

    with World(spec) as world:
        async with BrowserHarness() as harness:
            ctx, page = await harness.new_context()
            await page.goto(world.url, wait_until="networkidle")

            # Target an element that does not exist on the page
            missing_action = Action(
                id="act_missing",
                kind=ActionKind.CLICK,
                locator=Locator(
                    role="button",
                    name="Fake Completely Nonexistent Button 9999",
                    testid="fake-button-id",
                    css_fallback="#fake-id-12345",
                ),
            )
            ok, reason = await execute(page, missing_action, timeout_ms=1000)
            assert ok is False
            assert reason is not None
            assert "not_executable" in reason

            await ctx.close()
