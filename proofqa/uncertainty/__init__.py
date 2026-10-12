"""Uncertainty quantification, confidence scoring, tier assignment, and deduplication."""

from __future__ import annotations

from proofqa.uncertainty.scoring import (
    ConfidenceBreakdown,
    assign_tier,
    compute_confidence,
    deduplicate_findings,
    wilson_score_interval,
)

__all__ = [
    "ConfidenceBreakdown",
    "assign_tier",
    "compute_confidence",
    "deduplicate_findings",
    "wilson_score_interval",
]
