"""Uncertainty quantification, confidence scoring, tier assignment, and abstention."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from proofqa.contracts import (
    FailureSignature,
    Finding,
    OracleClass,
    Tier,
)


def wilson_score_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Calculate the Wilson score confidence interval for a binomial proportion."""
    if total == 0:
        return 0.0, 0.0

    p_hat = successes / total
    denom = 1.0 + (z**2 / total)
    centre = (p_hat + (z**2 / (2 * total))) / denom
    spread = (z / denom) * math.sqrt((p_hat * (1 - p_hat) / total) + (z**2 / (4 * total**2)))

    lower = max(0.0, centre - spread)
    upper = min(1.0, centre + spread)
    return lower, upper


@dataclass
class ConfidenceBreakdown:
    """Detailed audit log of confidence components."""

    reproduction_rate: float
    wilson_lower: float
    wilson_upper: float
    oracle_weight: float
    noise_floor_distance: float
    signature_stability: float
    composite_score: float
    details: dict[str, Any] = field(default_factory=dict)


def compute_confidence(
    finding: Finding,
    successes: int,
    total_replays: int,
    is_in_noise_floor: bool = False,
    is_signature_stable: bool = True,
) -> ConfidenceBreakdown:
    """Compute grounded confidence and assign components."""
    if total_replays == 0:
        rate = 0.0
        w_lower, w_upper = 0.0, 0.0
    else:
        rate = successes / total_replays
        w_lower, w_upper = wilson_score_interval(successes, total_replays)

    # Oracle strength weight
    class_weights = {
        OracleClass.A: 1.0,
        OracleClass.D: 0.95,
        OracleClass.B: 0.90,
        OracleClass.C: 0.85,
        OracleClass.E: 0.80,
        OracleClass.F: 0.75,
    }
    oracle_weight = class_weights.get(finding.oracle_class, 0.7)

    # Noise distance: 0.0 if present in clean noise profile, 1.0 if clean
    noise_distance = 0.0 if is_in_noise_floor else 1.0

    # Signature stability: 1.0 if consistent error type and endpoint
    sig_stability = 1.0 if is_signature_stable else 0.5

    # Composite score calculation
    if noise_distance == 0.0:
        composite = 0.1
    else:
        composite = (0.5 * rate) + (0.3 * oracle_weight) + (0.2 * sig_stability)

    return ConfidenceBreakdown(
        reproduction_rate=rate,
        wilson_lower=w_lower,
        wilson_upper=w_upper,
        oracle_weight=oracle_weight,
        noise_floor_distance=noise_distance,
        signature_stability=sig_stability,
        composite_score=round(composite, 4),
        details={
            "oracle_class": finding.oracle_class.value,
            "successes": successes,
            "total_replays": total_replays,
        },
    )


def assign_tier(
    finding: Finding,
    successes: int,
    total_replays: int,
    breakdown: ConfidenceBreakdown,
) -> tuple[Tier, bool, str | None]:
    """Assign grounded Tier, intent_confirmation_needed flag, and next experiment."""
    if breakdown.noise_floor_distance == 0.0 or (total_replays > 0 and successes == 0):
        # Weak signal or matches noise floor -> abstain
        next_exp = "Execute 5x throttled-network replay (latency=300ms) with clean isolated profile"
        return Tier.INSUFFICIENT_EVIDENCE, False, next_exp

    rate = breakdown.reproduction_rate

    # Intermittent bug (e.g. B09 add-to-cart failure rate ~33%)
    if 0.0 < rate < 1.0:
        return Tier.INTERMITTENT, False, None

    # Classes B, C, D, E require human intent confirmation
    if finding.oracle_class in (OracleClass.B, OracleClass.C, OracleClass.D, OracleClass.E):
        return Tier.VERIFIED_VIOLATION, True, None

    # Class A hard crash reproducing 100%
    if rate == 1.0:
        return Tier.VERIFIED, False, None

    return Tier.SUSPECTED, False, "Re-run 3 additional replays with varied network latency"


def deduplicate_findings(findings: list[Finding]) -> list[Finding]:
    """Deduplicate findings by failure fingerprint."""
    seen: dict[tuple[Any, ...], Finding] = {}
    for f in findings:
        sig: FailureSignature = f.signature
        key = (
            sig.kind,
            sig.first_party_endpoint,
            sig.status,
            sig.error_type,
            sig.message_norm,
        )
        if key not in seen:
            seen[key] = f
        else:
            # Preserve higher confidence or shorter steps
            existing = seen[key]
            if len(f.steps) < len(existing.steps) or f.confidence > existing.confidence:
                seen[key] = f

    return list(seen.values())
