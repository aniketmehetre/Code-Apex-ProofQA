"""Class B Metamorphic Oracle: evaluates behavioral invariants directly over tape events."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib.parse import parse_qs, urlparse

from proofqa.contracts import (
    Action,
    ActionKind,
    FailureSignature,
    Finding,
    OracleClass,
    Tier,
    normalize_message,
)


class MetamorphicOracle:
    """Class B Oracle inspecting tape actions and network events for metamorphic invariant violations."""

    def __init__(self) -> None:
        self.candidates: list[Finding] = []
        self._seen_signatures: set[str] = set()

        # State tracking for sort reversion (B05)
        self._initial_sort_ids: list[int | str] | None = None
        self._has_switched_sort: bool = False

        # State tracking for persistence across reload (B07)
        self._last_saved_address: str | None = None
        self._has_reloaded: bool = False

    def hook(
        self,
        fp: Any,
        action: Action,
        events: list[Any],
        action_prefix: list[Action],
    ) -> None:
        """Evaluated after every action transition."""
        findings = self.evaluate_transition(action, events, action_prefix)
        for f in findings:
            sig_key = f"{f.signature.kind}:{f.signature.first_party_endpoint}:{f.signature.message_norm}"
            if sig_key not in self._seen_signatures:
                self._seen_signatures.add(sig_key)
                self.candidates.append(f)

    def evaluate_transition(
        self,
        action: Action,
        events: list[Any],
        action_prefix: list[Action],
    ) -> list[Finding]:
        """Checks sort restoration, category filter purity, and address persistence invariants."""
        findings: list[Finding] = []

        # Track reload actions
        if action.kind == ActionKind.GOTO or (action.params and action.params.get("reload")):
            if self._last_saved_address:
                self._has_reloaded = True

        for ev in events:
            url = getattr(ev, "url", "")
            method = (getattr(ev, "method", "") or "GET").upper()
            status = getattr(ev, "status", 200)

            # Extract body if available
            body_dict: dict[str, Any] | None = getattr(ev, "body_json", None)
            if not body_dict:
                blob_ref = getattr(ev, "response_blob_ref", None)
                if blob_ref:
                    from proofqa.tape.recorder import GLOBAL_BLOB_CACHE
                    body_dict = GLOBAL_BLOB_CACHE.get(blob_ref)
                    if not body_dict:
                        try:
                            import glob
                            from pathlib import Path
                            candidates = [
                                Path("results/explore/blobs") / blob_ref,
                                Path("results/blobs") / blob_ref,
                                Path(blob_ref),
                            ]
                            for c in candidates:
                                if c.exists():
                                    body_dict = json.loads(c.read_text(encoding="utf-8"))
                                    break
                            if not body_dict:
                                found = glob.glob(f"**/blobs/{blob_ref}", recursive=True)
                                if found:
                                    body_dict = json.loads(Path(found[0]).read_text(encoding="utf-8"))
                        except Exception:
                            pass

            if not url:
                continue

            parsed = urlparse(url)
            path = parsed.path
            query = parse_qs(parsed.query)

            # -------------------------------------------------------------
            # Check 1: Category Filter Purity (B06)
            # -------------------------------------------------------------
            if path == "/api/products" and "category" in query and body_dict:
                cat_req = query["category"][0].strip().lower()
                items = body_dict.get("products") or body_dict.get("items", [])
                if isinstance(items, list):
                    leaked = [
                        it for it in items
                        if isinstance(it, dict) and it.get("category", "").strip().lower() != cat_req
                    ]
                    if leaked:
                        sig = FailureSignature(
                            kind="relation_violation",
                            first_party_endpoint="/api/products",
                            error_type="MetamorphicViolation",
                            message_norm=normalize_message(
                                "Category filter on page 2 returns items from other categories"
                            ),
                        )
                        fid = f"finding_B_{hashlib.sha256(sig.message_norm.encode()).hexdigest()[:8]}"
                        findings.append(
                            Finding(
                                id=fid,
                                oracle_class=OracleClass.B,
                                tier=Tier.VERIFIED_VIOLATION,
                                signature=sig,
                                claim="Category filter returns items from other categories (B06)",
                                steps=action_prefix + [action],
                                confidence=1.0,
                                intent_confirmation_needed=True,
                            )
                        )

            # -------------------------------------------------------------
            # Check 2: Sort Reversion Invariance (B05)
            # -------------------------------------------------------------
            if path == "/api/products" and method == "GET" and body_dict:
                sort_val = query.get("sort", [""])[0]
                items = body_dict.get("products") or body_dict.get("items", [])
                item_ids = [it.get("id") for it in items if isinstance(it, dict) and "id" in it]

                if not sort_val or sort_val in ("default", ""):
                    if self._initial_sort_ids is None and item_ids:
                        self._initial_sort_ids = item_ids
                    elif self._has_switched_sort and self._initial_sort_ids is not None:
                        # Returning to default sort MUST restore initial ordering
                        if item_ids != self._initial_sort_ids:
                            sig = FailureSignature(
                                kind="relation_violation",
                                first_party_endpoint="/api/products",
                                error_type="MetamorphicViolation",
                                message_norm=normalize_message(
                                    "Returning to default sort order does not restore initial ID ordering"
                                ),
                            )
                            fid = f"finding_B_{hashlib.sha256(sig.message_norm.encode()).hexdigest()[:8]}"
                            findings.append(
                                Finding(
                                    id=fid,
                                    oracle_class=OracleClass.B,
                                    tier=Tier.VERIFIED_VIOLATION,
                                    signature=sig,
                                    claim="Returning to default sort order does not restore initial ID ordering (B05)",
                                    steps=action_prefix + [action],
                                    confidence=1.0,
                                    intent_confirmation_needed=True,
                                )
                            )
                else:
                    self._has_switched_sort = True

            # -------------------------------------------------------------
            # Check 3: State Persistence Across Reload (B07)
            # -------------------------------------------------------------
            if path == "/api/account/address":
                if method in ("PUT", "POST", "PATCH") and 200 <= status < 300:
                    if action.kind == ActionKind.FILL and action.value:
                        self._last_saved_address = action.value
                elif method == "GET" and self._last_saved_address and self._has_reloaded:
                    fetched_addr = body_dict.get("address") if body_dict else None
                    if fetched_addr != self._last_saved_address:
                        sig = FailureSignature(
                            kind="relation_violation",
                            first_party_endpoint="/api/account/address",
                            error_type="MetamorphicViolation",
                            message_norm=normalize_message(
                                "Saved user account address is lost upon subsequent retrieval"
                            ),
                        )
                        fid = f"finding_B_{hashlib.sha256(sig.message_norm.encode()).hexdigest()[:8]}"
                        findings.append(
                            Finding(
                                id=fid,
                                oracle_class=OracleClass.B,
                                tier=Tier.VERIFIED_VIOLATION,
                                signature=sig,
                                claim="Saved user account address is lost upon subsequent retrieval (B07)",
                                steps=action_prefix + [action],
                                confidence=1.0,
                                intent_confirmation_needed=True,
                            )
                        )

        return findings
