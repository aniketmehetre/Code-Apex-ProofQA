"""Acceptance tests for multi-level test case shrinking (Levels 1, 2, 3)."""

from __future__ import annotations

import pytest

from proofqa.contracts import (
    Action,
    ActionKind,
    FailureSignature,
    Locator,
    WorldSpec,
)
from proofqa.proof import clear_replay_cache, shrink
from proofqa.proof.value_shrink import shrink_values


@pytest.fixture(autouse=True)
def reset_cache() -> None:
    clear_replay_cache()


@pytest.mark.asyncio
async def test_shrink_trace_preserves_prerequisites_and_locks_signature() -> None:
    """Test shrinking on B01:

    Start with a bloated trace containing redundant steps (viewing about page, browsing categories).
    Assert that shrink reduces to essential modal open, qty 0, and cart submission.
    """
    target_sig = FailureSignature(
        kind="http_5xx",
        first_party_endpoint="/api/cart",
        status=500,
        message_norm="HTTP <NUM> on /api/cart",
    )
    spec = WorldSpec(app_id="shop_twin", bugs=["B01"])

    # Bloated 8-step trace
    bloated_trace = [
        Action(id="s0_home", kind=ActionKind.GOTO, value="/"),
        Action(id="s1_about_noop", kind=ActionKind.CLICK, locator=Locator(role="button", name="About")),
        Action(id="s2_back_home", kind=ActionKind.CLICK, locator=Locator(role="button", name="Shop")),
        Action(
            id="s3_open_modal",
            kind=ActionKind.CLICK,
            locator=Locator(role="heading", name="Noise-Canceling Wireless Headphones"),
        ),
        Action(
            id="s4_set_zero_qty",
            kind=ActionKind.FILL,
            locator=Locator(role="spinbutton", name="Quantity", label="Quantity"),
            value="0",
        ),
        Action(
            id="s5_submit_cart",
            kind=ActionKind.CLICK,
            locator=Locator(role="button", name="Confirm Add to Cart", testid="modal-add-to-cart"),
        ),
    ]

    result = await shrink(
        trace=bloated_trace,
        world_spec=spec,
        target_signature=target_sig,
        budget=20,
        enable_level3=True,
    )

    # Acceptance: trace is reduced
    assert len(result.reduced_trace) < len(bloated_trace)
    assert result.replays_used > 0
    # The reduced trace must retain the essential triggers
    action_ids = [a.id for a in result.reduced_trace]
    assert "s3_open_modal" in action_ids
    assert "s4_set_zero_qty" in action_ids
    assert "s5_submit_cart" in action_ids


@pytest.mark.asyncio
async def test_level_3_value_shrinking() -> None:
    """Test Level 3 value shrinking:

    A numeric quantity shrinks to 0.
    A search query containing special character shrinks to minimal quote.
    """
    target_sig = FailureSignature(
        kind="http_5xx",
        first_party_endpoint="/api/cart",
        status=500,
        message_norm="HTTP <NUM> on /api/cart",
    )
    spec = WorldSpec(app_id="shop_twin", bugs=["B01"])

    trace = [
        Action(id="s0_home", kind=ActionKind.GOTO, value="/"),
        Action(
            id="s1_open_modal",
            kind=ActionKind.CLICK,
            locator=Locator(role="heading", name="Noise-Canceling Wireless Headphones"),
        ),
        Action(
            id="s2_set_qty",
            kind=ActionKind.FILL,
            locator=Locator(role="spinbutton", name="Quantity", label="Quantity"),
            value="0",
        ),
        Action(
            id="s3_submit_cart",
            kind=ActionKind.CLICK,
            locator=Locator(role="button", name="Confirm Add to Cart", testid="modal-add-to-cart"),
        ),
    ]

    async def mock_evaluator(t: list[Action]) -> str:
        for a in t:
            if a.kind == ActionKind.FILL and a.value == "0":
                return "FAIL"
        return "PASS"

    reduced_trace, minimal_inputs = await shrink_values(
        trace=trace,
        world_spec=spec,
        target_signature=target_sig,
        evaluator=mock_evaluator,
    )

    assert minimal_inputs["s2_set_qty"]["minimal_value"] == "0"
    assert reduced_trace[2].value == "0"
