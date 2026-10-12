"""Deliberately false metamorphic relation used to verify the validation gate."""

from __future__ import annotations

import hashlib
from typing import Any

from playwright.async_api import Page

from proofqa.contracts import (
    FailureSignature,
    Finding,
    OracleClass,
    Tier,
    WorldSpec,
    normalize_message,
)
from proofqa.oracles.relations.base import Relation


class DeliberatelyFalseRelation(Relation):
    """A mathematically false relation asserting an invalid invariant:

    Asserts that all products in the catalog have price $0.00.
    This relation MUST fail validate() on a clean reference world and be discarded.
    """

    name = "deliberately_false_relation"

    def applies(self, widgets: dict[str, Any]) -> bool:
        return True

    async def run(self, page: Page, world_url: str) -> Finding | None:
        # Fails invariant: claims all products must cost 0.00
        prices = page.locator(".product-price")
        count = await prices.count()
        if count > 0:
            sig = FailureSignature(
                kind="relation_violation",
                error_type="FalseRelationViolation",
                message_norm=normalize_message("FalseRelationViolation: Product prices are non-zero"),
            )
            fid = f"finding_B_{hashlib.sha256(sig.message_norm.encode('utf-8')).hexdigest()[:8]}"
            return Finding(
                id=fid,
                oracle_class=OracleClass.B,
                tier=Tier.VERIFIED_VIOLATION,
                signature=sig,
                claim="Deliberately false invariant failed",
                steps=[],
                confidence=1.0,
                intent_confirmation_needed=True,
            )
        return None

    async def validate(self, world_spec: WorldSpec) -> bool:
        """Always fails validation because the invariant is false."""
        return False
