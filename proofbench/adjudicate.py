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

            # Kind matching (exact or compatible family)
            exp_kind = exp.get("kind")
            sig_kind = sig.kind
            if exp_kind == sig_kind:
                kind_match = True
            elif exp_kind in ("http_5xx", "page_error") and sig_kind in ("http_5xx", "page_error"):
                kind_match = True
            elif exp_kind in ("ui_mismatch", "cross_layer_inconsistency") and sig_kind in ("ui_mismatch", "cross_layer_inconsistency"):
                kind_match = True
            elif exp_kind in ("relation_violation", "metamorphic") and sig_kind in ("relation_violation", "metamorphic"):
                kind_match = True
            elif exp_kind in ("spec_claim_violation", "spec_violation") and sig_kind in ("spec_claim_violation", "spec_violation"):
                kind_match = True
            else:
                kind_match = False

            if not kind_match:
                continue

            # Status matching
            if exp.get("status") is not None and sig.status is not None:
                if exp["status"] != sig.status:
                    continue

            # Endpoint matching
            if exp.get("first_party_endpoint") and sig.first_party_endpoint:
                if exp["first_party_endpoint"] != sig.first_party_endpoint:
                    continue

            # If both specify error_type, they must be consistent
            if exp.get("error_type") and sig.error_type and exp["error_type"].lower() not in sig.error_type.lower():
                continue

            # Disambiguate B01 vs B09 (both target /api/cart with 500)
            claim_text = (finding.claim or "").lower()
            msg_text = ((sig.message_norm or "") + " " + claim_text).lower()
            has_burst = any(getattr(a, "burst", 1) > 1 for a in finding.steps) or str(getattr(finding, "tier", "")) in ("Tier.INTERMITTENT", "INTERMITTENT")
            if bid == "B01" and (has_burst or "concurrency" in claim_text or "lock" in claim_text):
                continue
            if bid == "B09" and not (has_burst or "concurrency" in claim_text or "lock" in claim_text or "transient" in claim_text):
                continue

            # Disambiguate B03 vs B04 (both target /api/cart with CrossLayerMismatch)
            if bid == "B03" and ("total" in msg_text or "discount" in msg_text):
                continue
            if bid == "B04" and not ("total" in msg_text or "discount" in msg_text):
                continue

            # Disambiguate B05 vs B06 (both target /api/products with relation_violation)
            if bid == "B05" and not ("sort" in msg_text or "order" in msg_text or "restor" in msg_text):
                continue
            if bid == "B06" and not ("filter" in msg_text or "category" in msg_text or "page" in msg_text or "leak" in msg_text):
                continue

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
