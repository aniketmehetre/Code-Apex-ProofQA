"""Acceptance tests for Oracle Classes C (spec claims) and E (temporal differential)."""

from __future__ import annotations

import httpx
import pytest
from httpx import ASGITransport

from apps.shop_twin.backend.app import app
from proofqa.contracts import (
    Action,
    ActionKind,
    Locator,
    OracleClass,
    Tier,
    WorldSpec,
)
from proofqa.oracles.spec_claims import SpecClaimsOracle
from proofqa.oracles.temporal_diff import TemporalDifferentialOracle


@pytest.mark.asyncio
async def test_class_c_spec_claims_detects_b08(monkeypatch: pytest.MonkeyPatch) -> None:
    # 1. Page text containing spec claim
    about_text = "Security Policy: Password must be at least 8 characters in length."
    oracle = SpecClaimsOracle(offline=True)
    claims = oracle.extract_claims(about_text)

    assert len(claims) == 1
    assert claims[0]["quote_text"] == "Password must be at least 8 characters"
    assert claims[0]["quote_span"] == (17, 55)

    # 2. Test when B08 is ON: accepts 4-char password
    monkeypatch.setenv("BUGS", "B08")
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        finding = await oracle.verify_password_policy(client.post, claims[0], short_password="pass")

    assert finding is not None
    assert finding.oracle_class == OracleClass.C
    assert finding.tier == Tier.VERIFIED_VIOLATION
    assert "Password must be at least 8 characters" in finding.claim
    assert finding.intent_confirmation_needed is True

    # 3. Test when B08 is OFF: rejects short password, finding is None
    monkeypatch.setenv("BUGS", "")
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        clean_finding = await oracle.verify_password_policy(client.post, claims[0], short_password="pass")

    assert clean_finding is None


@pytest.mark.asyncio
async def test_class_e_temporal_differential_detects_divergence() -> None:
    baseline_spec = WorldSpec(app_id="shop_twin", bugs=[])
    candidate_spec = WorldSpec(app_id="shop_twin", bugs=["B01"])

    # Scripted trace for B01 (POST cart qty 0)
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

    oracle = TemporalDifferentialOracle()
    finding = await oracle.compare(trace, baseline_spec=baseline_spec, candidate_spec=candidate_spec, replays=1)

    assert finding is not None
    assert finding.oracle_class == OracleClass.E
    assert finding.tier == Tier.VERIFIED_VIOLATION
    assert finding.intent_confirmation_needed is True
