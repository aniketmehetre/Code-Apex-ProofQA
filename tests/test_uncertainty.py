"""Acceptance tests for Phase 8: Uncertainty quantification, tiers, and deduplication."""

from __future__ import annotations

from proofqa.contracts import (
    Action,
    ActionKind,
    FailureSignature,
    Finding,
    OracleClass,
    Tier,
)
from proofqa.uncertainty import (
    assign_tier,
    compute_confidence,
    deduplicate_findings,
    wilson_score_interval,
)


def test_wilson_score_interval_properties() -> None:
    # 10 successes out of 10
    lower, upper = wilson_score_interval(10, 10)
    assert 0.65 < lower <= 1.0
    assert upper == 1.0

    # 3 successes out of 10
    lower, upper = wilson_score_interval(3, 10)
    assert 0.0 < lower < 0.3
    assert 0.3 < upper < 1.0


def test_b09_intermittent_classification() -> None:
    sig = FailureSignature(
        kind="http_5xx",
        first_party_endpoint="/api/cart",
        status=500,
        message_norm="HTTP 500 on /api/cart",
    )
    finding = Finding(
        id="f_b09",
        oracle_class=OracleClass.A,
        tier=Tier.SUSPECTED,
        signature=sig,
        claim="Intermittent 500 on add to cart",
    )

    # 3 successes out of 9 replays (~33% rate)
    breakdown = compute_confidence(finding, successes=3, total_replays=9)
    tier, intent_needed, exp = assign_tier(finding, successes=3, total_replays=9, breakdown=breakdown)

    assert tier == Tier.INTERMITTENT
    assert intent_needed is False
    assert round(breakdown.reproduction_rate, 2) == 0.33


def test_b05_verified_violation_with_flag() -> None:
    sig = FailureSignature(
        kind="relation_violation",
        error_type="SortRestorationViolation",
        message_norm="SortRestorationViolation",
    )
    finding = Finding(
        id="f_b05",
        oracle_class=OracleClass.B,
        tier=Tier.SUSPECTED,
        signature=sig,
        claim="Default sort order corrupted",
    )

    breakdown = compute_confidence(finding, successes=3, total_replays=3)
    tier, intent_needed, exp = assign_tier(finding, successes=3, total_replays=3, breakdown=breakdown)

    assert tier == Tier.VERIFIED_VIOLATION
    assert intent_needed is True


def test_decoy_weak_signal_abstains_with_suggested_experiment() -> None:
    sig = FailureSignature(
        kind="console_error",
        error_type="TelemetryError",
        message_norm="Telemetry error",
    )
    finding = Finding(
        id="f_decoy",
        oracle_class=OracleClass.A,
        tier=Tier.SUSPECTED,
        signature=sig,
        claim="Weak third-party anomaly",
    )

    # Signal present in noise floor
    breakdown = compute_confidence(finding, successes=1, total_replays=3, is_in_noise_floor=True)
    tier, intent_needed, exp = assign_tier(finding, successes=1, total_replays=3, breakdown=breakdown)

    assert tier == Tier.INSUFFICIENT_EVIDENCE
    assert exp is not None
    assert "throttled-network replay" in exp


def test_deduplication_collapses_identical_fingerprints() -> None:
    sig = FailureSignature(
        kind="http_5xx",
        first_party_endpoint="/api/cart",
        status=500,
        message_norm="HTTP 500 on /api/cart",
    )
    f1 = Finding(
        id="dup_1",
        oracle_class=OracleClass.A,
        tier=Tier.VERIFIED,
        signature=sig,
        claim="Claim 1",
        steps=[Action(id="a0", kind=ActionKind.GOTO, value="/")],
        confidence=0.8,
    )
    f2 = Finding(
        id="dup_2",
        oracle_class=OracleClass.A,
        tier=Tier.VERIFIED,
        signature=sig,
        claim="Claim 2",
        steps=[
            Action(id="a0", kind=ActionKind.GOTO, value="/"),
            Action(id="a1", kind=ActionKind.CLICK),
        ],
        confidence=0.9,
    )

    deduped = deduplicate_findings([f1, f2])
    assert len(deduped) == 1
    assert deduped[0].id == "dup_1" or deduped[0].confidence == 0.9
