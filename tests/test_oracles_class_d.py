"""Acceptance tests for Class D Cross-Layer Consistency Oracle detecting B03 and B04."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from proofqa.contracts import Action, ActionKind, OracleClass, WorldSpec
from proofqa.oracles import CrossLayerOracle
from proofqa.world import World


@pytest.mark.asyncio
async def test_cross_layer_oracle_detects_b03_and_b04() -> None:
    oracle = CrossLayerOracle(tolerance=0.01, settle_delay_seconds=0.01)

    # 1. Test B03: Cart badge mismatch (UI shows 2, API says 1)
    mock_page_b03 = MagicMock()
    mock_badge = MagicMock()
    mock_badge.count = AsyncMock(return_value=1)
    mock_badge.first.is_visible = AsyncMock(return_value=True)
    mock_badge.first.text_content = AsyncMock(return_value="2")  # B03: +1 error

    mock_total = MagicMock()
    mock_total.count = AsyncMock(return_value=0)

    mock_pcount = MagicMock()
    mock_pcount.count = AsyncMock(return_value=0)

    mock_rows = MagicMock()
    mock_rows.count = AsyncMock(return_value=0)

    def locator_side_effect(selector: str):
        if "cart-badge" in selector:
            return mock_badge
        if "cart-total" in selector:
            return mock_total
        if "product-count" in selector:
            return mock_pcount
        return mock_rows

    mock_page_b03.locator.side_effect = locator_side_effect

    api_b03 = {"/api/cart": {"item_count": 1, "items": [{"id": 1, "quantity": 1}], "total": 10.0}}
    act = Action(id="remove_item", kind=ActionKind.CLICK)
    results_b03 = await oracle.verify_consistency(mock_page_b03, api_b03, [act])

    assert len(results_b03) == 1
    event_b03, finding_b03 = results_b03[0]
    assert event_b03.label == "cart_badge_count"
    assert event_b03.ui_value == 2
    assert event_b03.api_value == 1
    assert finding_b03 is not None
    assert finding_b03.oracle_class == OracleClass.D
    assert "cart_badge_count" in finding_b03.signature.message_norm

    # 2. Test B04: Cart total mismatch (UI displays $149.99 ignoring coupon, API total is $134.99)
    mock_page_b04 = MagicMock()
    mock_total_b04 = MagicMock()
    mock_total_b04.count = AsyncMock(return_value=1)
    mock_total_b04.first.is_visible = AsyncMock(return_value=True)
    mock_total_b04.first.text_content = AsyncMock(return_value="$149.99")  # B04 bug

    def locator_b04(selector: str):
        if "cart-total" in selector:
            return mock_total_b04
        return mock_badge  # badge count 1

    mock_badge.first.text_content = AsyncMock(return_value="1")
    mock_page_b04.locator.side_effect = locator_b04

    api_b04 = {"/api/cart": {"item_count": 1, "total": 134.99}}
    results_b04 = await oracle.verify_consistency(mock_page_b04, api_b04, [act])

    # Should detect total mismatch
    findings = [f for _, f in results_b04 if f is not None]
    assert len(findings) == 1
    f_total = findings[0]
    assert f_total.oracle_class == OracleClass.D
    assert "cart_total" in f_total.signature.message_norm


@pytest.mark.asyncio
async def test_cross_layer_oracle_zero_false_positives_on_clean_state() -> None:
    oracle = CrossLayerOracle(tolerance=0.01, settle_delay_seconds=0.01)

    spec = WorldSpec(app_id="shop_twin", bugs=[])
    world = World(spec)

    with world:
        from proofqa.browser.harness import BrowserHarness
        h = BrowserHarness()
        async with h:
            context, page = await h.new_context()
            await page.goto(f"{world.url}/", wait_until="networkidle")

            # Clean state with no items: cart badge is not displayed or empty, catalog matches
            api_data = {
                "/api/cart": {"item_count": 0, "items": [], "total": 0.0},
                "/api/products": {"total": 60, "products": []},
            }
            results = await oracle.verify_consistency(page, api_data, [])

            # Acceptance: Zero false positives on a clean twin
            findings = [f for _, f in results if f is not None]
            assert len(findings) == 0
            assert len(oracle.candidates) == 0
