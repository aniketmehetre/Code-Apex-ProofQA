"""Tests for Prompt 8: Burst actions, INTERMITTENT tier, and negative controls for B09.

Verifies:
1. Burst actions dispatch concurrent clicks.
2. B09 intermittent defect is detected and certified under Tier.INTERMITTENT.
3. verify_certificate returns VALID_INTERMITTENT for m-of-n reproducing certificates.
4. 30-run negative control with B09 disabled yields 0 signature hits.
5. Decoy D10 (friendly 429) stays clean and produces 0 false positive findings.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofqa.cert import build_certificate, verify_certificate
from proofqa.contracts import (
    Action,
    ActionKind,
    FailureSignature,
    Finding,
    Locator,
    OracleClass,
    Tier,
    VerifyVerdictKind,
    WorldSpec,
)
from proofqa.proof.replay import replay


@pytest.fixture
def b09_burst_trace() -> tuple[list[Action], FailureSignature]:
    """Reproducing trace for B09: rapid concurrent clicks on Add to Cart."""
    actions = [
        Action(id="s0_home", kind=ActionKind.GOTO, value="/"),
        Action(
            id="s1_burst_add_to_cart",
            kind=ActionKind.CLICK,
            locator=Locator(testid="add-to-cart-1"),
            burst=5,
        ),
    ]
    sig = FailureSignature(
        kind="http_5xx",
        first_party_endpoint="/api/cart",
        status=500,
        message_norm="HTTP <NUM> on /api/cart",
    )
    return actions, sig


@pytest.mark.asyncio
async def test_burst_action_b09_intermittent_repro_and_verify(
    tmp_path: Path, b09_burst_trace: tuple[list[Action], FailureSignature]
) -> None:
    """Verifies that burst trace triggers B09, certifies under INTERMITTENT tier, and verifies as VALID_INTERMITTENT."""
    trace, sig = b09_burst_trace
    spec = WorldSpec(app_id="shop_twin", bugs=["B09"], seed=42)

    # 1. Run 5 replays
    rep = await replay(
        trace=trace,
        world_spec=spec,
        n=5,
        target_signature=sig,
        concurrency=1,
    )

    # Sanity math: at 0.34 per request, a 5-burst triggers ~87% per run. 2-of-5 passes ~99.9%.
    assert rep.fail_count >= 2, f"Expected at least 2/5 failures for B09, got {rep.fail_count}/5"

    observed_rate = f"{rep.fail_count}/{rep.total}"

    finding = Finding(
        id="cert_b09_intermittent",
        oracle_class=OracleClass.A,
        tier=Tier.INTERMITTENT,
        signature=sig,
        claim="Rapid concurrent cart addition triggers transient LockTimeoutException (B09)",
        steps=trace,
        confidence=float(rep.fail_count) / float(rep.total),
        observed_rate=observed_rate,
    )

    # 2. Build certificate
    cert_dir = build_certificate(
        finding=finding,
        world_spec=spec,
        output_dir=tmp_path,
        replay_report=rep,
    )

    claim_data = json.loads((cert_dir / "claim.json").read_text(encoding="utf-8"))
    assert claim_data["tier"] == "INTERMITTENT"
    assert "observed_rate" in claim_data
    assert claim_data["observed_rate"] == observed_rate

    # 3. Verify certificate -> VALID_INTERMITTENT
    verdict = await verify_certificate(cert_dir, replay_count=5, verbose=False)
    assert verdict.verdict == VerifyVerdictKind.VALID_INTERMITTENT
    assert "meets m-of-n" in (verdict.reason or "")


@pytest.mark.asyncio
async def test_b09_negative_control_30_runs(
    b09_burst_trace: tuple[list[Action], FailureSignature]
) -> None:
    """Negative control: 30 burst runs with B09 disabled must yield EXACTLY 0 signature hits."""
    trace, sig = b09_burst_trace
    clean_spec = WorldSpec(app_id="shop_twin", bugs=[], seed=100)

    # Run 30 replays
    rep = await replay(
        trace=trace,
        world_spec=clean_spec,
        n=30,
        target_signature=sig,
        concurrency=2,
    )

    assert rep.fail_count == 0, f"Expected 0 failures on clean negative control, got {rep.fail_count}"
    assert rep.pass_count == 30, f"Expected all 30 runs to pass cleanly, got {rep.pass_count}"


@pytest.mark.asyncio
async def test_b09_burst_against_decoy_d10(
    b09_burst_trace: tuple[list[Action], FailureSignature]
) -> None:
    """Decoy D10 (friendly 429 on rapid endpoint hits) must stay clean (0 false positives)."""
    trace, sig = b09_burst_trace
    d10_spec = WorldSpec(app_id="shop_twin", bugs=["D10"], seed=200)

    rep = await replay(
        trace=trace,
        world_spec=d10_spec,
        n=5,
        target_signature=sig,
        concurrency=1,
    )

    # Target signature is 500 LockTimeoutException; D10 returns 429, so 0 signature hits
    assert rep.fail_count == 0, f"Decoy D10 should not match 500 error signature, got {rep.fail_count} hits"
    assert rep.pass_count == 5
