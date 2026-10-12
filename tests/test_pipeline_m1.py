"""Acceptance tests for Milestone M1 (Prompt 7.1 Vertical Slice Pipeline)."""

from __future__ import annotations

from pathlib import Path

import pytest

from proofqa.cert.verify import verify_certificate
from proofqa.contracts import VerifyVerdictKind, WorldSpec
from proofqa.pipeline import Pipeline


@pytest.mark.asyncio
async def test_pipeline_produces_valid_certificates_on_buggy_world(tmp_path: Path) -> None:
    from proofqa.contracts import (
        Action,
        ActionKind,
        FailureSignature,
        Finding,
        Locator,
        OracleClass,
        Tier,
    )

    # Scripted candidate for B01
    sig = FailureSignature(
        kind="http_5xx",
        first_party_endpoint="/api/cart",
        status=500,
        message_norm="HTTP <NUM> on /api/cart",
    )
    spec = WorldSpec(app_id="shop_twin", bugs=["B01"])
    candidate = Finding(
        id="finding_b01_vertical_slice",
        oracle_class=OracleClass.A,
        tier=Tier.VERIFIED,
        signature=sig,
        claim="Zero quantity cart addition produces HTTP 500 (B01)",
        steps=[
            Action(id="s0", kind=ActionKind.GOTO, value="/"),
            Action(id="s1_noop", kind=ActionKind.CLICK, locator=Locator(role="button", name="About")),
            Action(id="s2_back", kind=ActionKind.CLICK, locator=Locator(role="button", name="Shop")),
            Action(id="s3", kind=ActionKind.CLICK, locator=Locator(role="heading", name="Noise-Canceling Wireless Headphones")),
            Action(id="s4", kind=ActionKind.FILL, locator=Locator(role="spinbutton", name="Quantity", label="Quantity"), value="0"),
            Action(id="s5", kind=ActionKind.CLICK, locator=Locator(role="button", name="Confirm Add to Cart", testid="modal-add-to-cart")),
        ],
        confidence=1.0,
    )

    pipeline = Pipeline(
        world_spec=spec,
        output_dir=tmp_path / "certificates",
        session_db_path=tmp_path / "session.db",
    )

    certs = await pipeline.run(k_replays=1, initial_candidates=[candidate])

    # Acceptance: issued certificates and verified
    assert len(certs) == 1
    for cert_dir in certs:
        verdict = await verify_certificate(cert_dir, replay_count=1, verbose=False)
        assert verdict.verdict == VerifyVerdictKind.VALID


@pytest.mark.asyncio
async def test_pipeline_clean_world_produces_zero_certificates(tmp_path: Path) -> None:
    # Clean world: no bugs
    spec = WorldSpec(app_id="shop_twin", bugs=[])
    pipeline = Pipeline(
        world_spec=spec,
        output_dir=tmp_path / "certificates",
        session_db_path=tmp_path / "session.db",
    )

    certs = await pipeline.run(step_budget=10, k_replays=1)

    # Acceptance: Zero false positive certificates issued on clean world
    assert len(certs) == 0
