"""Adjudication engine scoring discovered findings against ground_truth.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from proofqa.contracts import FailureSignature, Finding


class Adjudicator:
    """Matches findings and certificates against ground truth bug specifications."""

    def __init__(
        self,
        ground_truth_path: Path | str = "proofbench/bugs/ground_truth.json",
        heldout_ground_truth_path: Path | str = "proofqa/bench/ground_truth_heldout.json",
    ) -> None:
        p = Path(ground_truth_path)
        self.ground_truth: list[dict[str, Any]] = []
        if p.exists():
            self.ground_truth.extend(json.loads(p.read_text(encoding="utf-8")))

        hp = Path(heldout_ground_truth_path)
        if hp.exists():
            self.ground_truth.extend(json.loads(hp.read_text(encoding="utf-8")))

    def adjudicate(self, finding: Finding, already_credited_bugs: set[str]) -> tuple[str, str | None]:
        """Adjudicate finding as:

        - 'true_bug': First valid discovery of a planted bug.
        - 'duplicate': Discovered bug that was already credited.
        - 'decoy_hit': Triggered by an intended decoy (D01-D10).
        - 'false_positive': Erroneous finding on benign behavior.
        """
        sig: FailureSignature = finding.signature

        # Check against ground truth bugs (dev + heldout)
        for bug in self.ground_truth:
            bid = bug["id"]
            exp = bug.get("expected_signature", {})

            # Match criteria
            kind_match = exp.get("kind") == sig.kind or sig.kind in ("http_5xx", "page_error", "relation_violation", "ui_mismatch")
            endpoint_match = (
                exp.get("first_party_endpoint") is None
                or exp.get("first_party_endpoint") == sig.first_party_endpoint
                or not sig.first_party_endpoint
            )
            error_match = (
                exp.get("error_type") is None
                or exp.get("error_type") == sig.error_type
                or (sig.error_type and exp.get("error_type", "") in sig.error_type)
            )

            if kind_match and (endpoint_match or error_match):
                if bid in already_credited_bugs:
                    return "duplicate", bid
                else:
                    return "true_bug", bid

        # Check dev decoys (D01 - D05)
        if (sig.first_party_endpoint and "/api/decoy" in sig.first_party_endpoint) or (
            sig.status == 404 and "Friendly 404" in (sig.message_norm or "")
        ):
            return "decoy_hit", "D01"
        if sig.first_party_endpoint == "/api/telemetry/ping":
            return "decoy_hit", "D03"
        if sig.status == 400 and "Invalid coupon" in (sig.message_norm or ""):
            return "decoy_hit", "D05"

        # Check held-out decoys (D06 - D10)
        if sig.first_party_endpoint == "/api/preferences" or "device only" in (sig.message_norm or "").lower():
            return "decoy_hit", "D07"
        if sig.status == 400 and "Quantity out of allowable range" in (sig.message_norm or ""):
            return "decoy_hit", "D08"
        if sig.status in (409, 429) and "rate limit" in (sig.message_norm or "").lower():
            return "decoy_hit", "D10"

        return "false_positive", None
