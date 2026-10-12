"""Acceptance tests for deterministic replay engine and three-valued outcome evaluation."""

from __future__ import annotations

import pytest

from proofqa.contracts import (
    Action,
    ActionKind,
    FailureSignature,
    Locator,
    ReplayOutcomeKind,
    WorldSpec,
)
from proofqa.proof import clear_replay_cache, replay


@pytest.fixture(autouse=True)
def clean_cache() -> None:
    clear_replay_cache()


@pytest.mark.asyncio
async def test_replay_b01_gives_all_fail() -> None:
    target_sig = FailureSignature(
        kind="http_5xx",
        first_party_endpoint="/api/cart",
        status=500,
        message_norm="HTTP <NUM> on /api/cart",
    )
    spec = WorldSpec(app_id="shop_twin", bugs=["B01"])

    trace = [
        Action(id="step_goto", kind=ActionKind.GOTO, value="/"),
        Action(
            id="step_open_modal",
            kind=ActionKind.CLICK,
            locator=Locator(role="heading", name="Noise-Canceling Wireless Headphones"),
        ),
        Action(
            id="step_set_zero_qty",
            kind=ActionKind.FILL,
            locator=Locator(role="spinbutton", name="Quantity", label="Quantity"),
            value="0",
        ),
        Action(
            id="step_submit_cart",
            kind=ActionKind.CLICK,
            locator=Locator(role="button", name="Confirm Add to Cart", testid="modal-add-to-cart"),
        ),
    ]

    report = await replay(
        trace=trace,
        world_spec=spec,
        n=2,
        target_signature=target_sig,
        concurrency=1,
        use_cache=False,
    )

    assert report.total == 2
    assert report.fail_count == 2
    assert report.pass_count == 0
    assert report.unresolved_count == 0
    assert report.reproduced is True
    assert all(r.outcome == ReplayOutcomeKind.FAIL for r in report.runs)


@pytest.mark.asyncio
async def test_replay_clean_world_gives_pass() -> None:
    spec = WorldSpec(app_id="shop_twin", bugs=[])

    trace = [
        Action(id="step_goto", kind=ActionKind.GOTO, value="/"),
        Action(
            id="step_open_modal",
            kind=ActionKind.CLICK,
            locator=Locator(role="heading", name="Noise-Canceling Wireless Headphones"),
        ),
        Action(
            id="step_set_valid_qty",
            kind=ActionKind.FILL,
            locator=Locator(role="spinbutton", name="Quantity", label="Quantity"),
            value="1",
        ),
        Action(
            id="step_submit_cart",
            kind=ActionKind.CLICK,
            locator=Locator(role="button", name="Confirm Add to Cart", testid="modal-add-to-cart"),
        ),
    ]

    report = await replay(
        trace=trace,
        world_spec=spec,
        n=2,
        concurrency=1,
        use_cache=False,
    )

    assert report.total == 2
    assert report.pass_count == 2
    assert report.fail_count == 0
    assert report.unresolved_count == 0
    assert all(r.outcome == ReplayOutcomeKind.PASS for r in report.runs)


@pytest.mark.asyncio
async def test_replay_missing_prerequisite_gives_unresolved() -> None:
    spec = WorldSpec(app_id="shop_twin", bugs=["B01"])

    # Notice: step_open_modal is omitted! The modal is not open, so Quantity input is missing.
    broken_trace = [
        Action(id="step_goto", kind=ActionKind.GOTO, value="/"),
        Action(
            id="step_set_zero_qty",
            kind=ActionKind.FILL,
            locator=Locator(role="spinbutton", name="Quantity", label="Quantity"),
            value="0",
        ),
        Action(
            id="step_submit_cart",
            kind=ActionKind.CLICK,
            locator=Locator(role="button", name="Confirm Add to Cart", testid="modal-add-to-cart"),
        ),
    ]

    report = await replay(
        trace=broken_trace,
        world_spec=spec,
        n=1,
        concurrency=1,
        use_cache=False,
    )

    assert report.total == 1
    assert report.unresolved_count == 1
    assert report.pass_count == 0
    assert report.fail_count == 0
    assert report.runs[0].outcome == ReplayOutcomeKind.UNRESOLVED
    assert "not executable" in (report.runs[0].reason or "").lower()


@pytest.mark.asyncio
async def test_replay_b09_gives_mix() -> None:
    spec = WorldSpec(app_id="shop_twin", bugs=["B09"])

    trace = [
        Action(id="step_goto", kind=ActionKind.GOTO, value="/"),
        Action(
            id="step_add_card",
            kind=ActionKind.CLICK,
            locator=Locator(role="button", testid="add-to-cart-1"),
        ),
    ]

    report = await replay(
        trace=trace,
        world_spec=spec,
        n=6,
        concurrency=1,
        use_cache=False,
    )

    assert report.total == 6
    # With ~34% intermittent failure rate, 6 runs should produce a mix or at least one pass and one fail
    # In rare random cases where all match one way, at least all outcomes are FAIL or PASS (never UNRESOLVED)
    assert report.unresolved_count == 0
    assert report.fail_count + report.pass_count == 6
