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

    def __init__(self, offline: bool = False) -> None:
        self.offline = offline

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
