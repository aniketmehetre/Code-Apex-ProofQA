"""Adjudication engine scoring discovered findings against ground_truth.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from proofqa.contracts import FailureSignature, Finding


class Adjudicator:
    """Matches findings and certificates against ground truth bug specifications."""

    def __init__(self, ground_truth_path: Path | str = "proofbench/bugs/ground_truth.json") -> None:
        p = Path(ground_truth_path)
        if p.exists():
            self.ground_truth: list[dict[str, Any]] = json.loads(p.read_text(encoding="utf-8"))
        else:
            self.ground_truth = []

    def adjudicate(self, finding: Finding, already_credited_bugs: set[str]) -> tuple[str, str | None]:
        """Adjudicate finding as:

        - 'true_bug': First valid discovery of a planted bug.
        - 'duplicate': Discovered bug that was already credited.
        - 'decoy_hit': Triggered by an intended decoy (D01-D05).
        - 'false_positive': Erroneous finding on benign behavior.
        """
        sig: FailureSignature = finding.signature

        # Check against ground truth bugs
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

        # Check decoys
        if sig.first_party_endpoint and "/api/decoy" in sig.first_party_endpoint:
            return "decoy_hit", None
        if sig.status == 404 and "Friendly 404" in (sig.message_norm or ""):
            return "decoy_hit", None

        return "false_positive", None
