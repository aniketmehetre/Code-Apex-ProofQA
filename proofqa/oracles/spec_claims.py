"""Oracle Class C: Specification claims extraction and deterministic verification."""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

from proofqa.contracts import (
    Action,
    ActionKind,
    FailureSignature,
    Finding,
    Locator,
    OracleClass,
    Tier,
    normalize_message,
)


class SpecClaimsOracle:
    """Class C Oracle: Extracts verifiable claims with exact quote spans and checks them deterministically."""

    def __init__(self, offline: bool = False, fact_store: Any = None) -> None:
        self.offline = offline
        self.fact_store = fact_store
        self.candidates: list[Finding] = []

    def hook(
        self,
        fp: Any,
        action: Action,
        events: list[Any],
        action_prefix: list[Action],
    ) -> None:
        """Oracle hook evaluated after every action step."""
        finding = self.evaluate_transition(self.fact_store, action, events, action_prefix)
        if finding and not any(c.signature == finding.signature for c in self.candidates):
            self.candidates.append(finding)

    def extract_claims(self, about_text: str) -> list[dict[str, Any]]:
        """Extract claims with quote span from page text.

        In OFFLINE mode or default fallback, uses deterministic regex/phrase matching.
        """
        claims: list[dict[str, Any]] = []

        # Claim: Minimum password length 8
        target_phrase = "Password must be at least 8 characters"
        if target_phrase.lower() in about_text.lower():
            start_idx = about_text.lower().index(target_phrase.lower())
            exact_quote = about_text[start_idx : start_idx + len(target_phrase)]
            claims.append({
                "id": "claim_password_length",
                "property": "min_password_length",
                "expected_min": 8,
                "quote_span": (start_idx, start_idx + len(target_phrase)),
                "quote_text": exact_quote,
            })

        return claims

    async def verify_password_policy(
        self,
        api_client_post: Any,
        claim: dict[str, Any],
        short_password: str = "pass",
    ) -> Finding | None:
        """Deterministically test password policy claim (B08).

        If the registration accepts a short password contrary to the specification quote,
        issue a Class C Finding citing the exact quote span.
        """
        response = await api_client_post(
            "/api/register",
            json={
                "email": f"claim_test_{uuid.uuid4().hex[:8]}@example.com",
                "password": short_password,
                "name": "Claim Verification User",
            },
        )

        # If registration succeeds with a 4-char password when policy says >= 8:
        if response.status_code == 200 or response.status_code == 201:
            quote = claim.get("quote_text", "Password must be at least 8 characters")
            span = claim.get("quote_span", (0, len(quote)))
            sig = FailureSignature(
                kind="spec_claim_violation",
                first_party_endpoint="/api/register",
                status=response.status_code,
                error_type="SpecClaimViolation",
                message_norm=normalize_message(
                    f"SpecClaimViolation: Registered with password length {len(short_password)} < 8 contrary to spec: '{quote}' [span {span[0]}:{span[1]}]"
                ),
            )
            fid = f"finding_C_{hashlib.sha256(sig.message_norm.encode()).hexdigest()[:8]}"
            return Finding(
                id=fid,
                oracle_class=OracleClass.C,
                tier=Tier.VERIFIED_VIOLATION,
                signature=sig,
                claim=f"Registration accepts {len(short_password)}-character password despite spec claim: '{quote}'",
                steps=[
                    Action(
                        id="c_register_short_pw",
                        kind=ActionKind.FILL,
                        locator=Locator(label="Password"),
                        value=short_password,
                    ),
                    Action(
                        id="c_submit_reg",
                        kind=ActionKind.CLICK,
                        locator=Locator(role="button", name="Register"),
                    ),
                ],
                confidence=1.0,
                intent_confirmation_needed=True,
            )

        return None

    def evaluate_transition(
        self,
        fact_store: Any,
        action: Action,
        events: list[Any],
        action_prefix: list[Action],
    ) -> Finding | None:
        """Evaluates a transition against explicit facts in the SpecFactStore.

        FAIL only if:
        (a) an explicit fact with source evidence exists in fact_store,
        (b) the filled value violates that fact, and
        (c) a first-party write in the same transition returned 2xx.
        """
        if action.kind != ActionKind.FILL or not action.value or not action.locator:
            return None

        if not fact_store:
            return None

        # Look for 2xx first-party write in events
        write_response = None
        for ev in events:
            ev_type = getattr(ev, "type", None) or getattr(ev, "kind", None)
            if ev_type == "network":
                st = getattr(ev, "status", 0)
                method = (getattr(ev, "method", "") or "GET").upper()
                url = getattr(ev, "url", "")
                if method in ("POST", "PUT", "PATCH", "DELETE") and 200 <= st < 300:
                    write_response = {"status": st, "method": method, "url": url}
                    break
            elif ev_type == "network_response":
                payload = getattr(ev, "payload", {}) or (ev if isinstance(ev, dict) else {})
                st = payload.get("status", 0)
                method = (payload.get("method") or "GET").upper()
                if method in ("POST", "PUT", "PATCH", "DELETE") and 200 <= st < 300:
                    write_response = payload
                    break

        if not write_response:
            return None

        loc_text = " ".join(filter(None, [action.locator.name, action.locator.label, action.locator.testid])).lower()
        subject = None
        for kw in ["password", "quantity", "email", "address", "phone"]:
            if kw in loc_text:
                subject = kw
                break

        if not subject:
            return None

        facts = fact_store.get_facts(subject)
        if not facts:
            return None

        violated_fact = None
        val_str = action.value
        for fact in facts:
            if fact.kind == "min_len":
                if len(val_str) < int(fact.value):
                    violated_fact = fact
                    break
            elif fact.kind == "max_len":
                if len(val_str) > int(fact.value):
                    violated_fact = fact
                    break
            elif fact.kind == "min":
                try:
                    if float(val_str) < float(fact.value):
                        violated_fact = fact
                        break
                except ValueError:
                    pass
            elif fact.kind == "max":
                try:
                    if float(val_str) > float(fact.value):
                        violated_fact = fact
                        break
                except ValueError:
                    pass

        if not violated_fact:
            return None

        ep = write_response.get("url", "").split("?")[0]
        ep_path = "/" + ep.split("/", 3)[-1] if "://" in ep else ep
        st = write_response.get("status", 200)

        sig = FailureSignature(
            kind="spec_claim_violation",
            first_party_endpoint=ep_path,
            status=st,
            error_type="SpecClaimViolation",
            message_norm=normalize_message(
                f"SpecClaimViolation: {subject} value '{val_str}' violates {violated_fact.kind}={violated_fact.value} on {violated_fact.page} citing: '{violated_fact.evidence_text}'"
            ),
        )
        fid = f"finding_C_{hashlib.sha256(sig.message_norm.encode()).hexdigest()[:8]}"
        return Finding(
            id=fid,
            oracle_class=OracleClass.C,
            tier=Tier.VERIFIED_VIOLATION,
            signature=sig,
            claim=f"Server returned {st} accepting {subject} value '{val_str}' contrary to spec fact: '{violated_fact.evidence_text}' on {violated_fact.page}",
            steps=action_prefix + [action],
            confidence=1.0,
            intent_confirmation_needed=True,
        )

