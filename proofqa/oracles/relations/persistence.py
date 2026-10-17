"""Metamorphic relation: state persistence and reload idempotency invariant."""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

from playwright.async_api import Page

from proofqa.browser.harness import BrowserHarness
from proofqa.contracts import (
    Action,
    ActionKind,
    FailureSignature,
    Finding,
    Locator,
    OracleClass,
    Tier,
    WorldSpec,
    normalize_message,
)
from proofqa.oracles.relations.base import Relation
from proofqa.world.manager import World


class AddressPersistenceRelation(Relation):
    """Save-then-reload metamorphic invariant:

    A shipping address saved to the authenticated user account MUST persist identically
    following a browser page reload.
    """

    name = "address_persistence_invariant"

    def applies(self, widgets: dict[str, Any]) -> bool:
        return True  # Applies to account checkout flow

    async def run(self, page: Page, world_url: str) -> Finding | None:
        # 1. Navigate to world
        await page.goto(f"{world_url}/", wait_until="networkidle")
        unique_user = f"persist_{uuid.uuid4().hex[:6]}"
        test_address = "777 Memory Lane, Suite 100"

        # 2. Register disposable user and save address using the page's origin session
        reg_ok = await page.evaluate(
            """async ({ user, address }) => {
                const regRes = await fetch('/api/register', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ email: `${user}@example.com`, password: 'Password123!', name: 'Persist User' })
                });
                if (!regRes.ok) return false;
                const putRes = await fetch('/api/account/address', {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ address: address })
                });
                return putRes.ok;
            }""",
            {"user": unique_user, "address": test_address},
        )
        if not reg_ok:
            return None

        # 3. Reload page to test persistence across page lifecycle
        await page.reload(wait_until="networkidle")

        # 4. Query persisted address from the reloaded page session
        fetched = await page.evaluate(
            """async () => {
                const res = await fetch('/api/account/address');
                if (!res.ok) return null;
                const data = await res.json();
                return data.address;
            }"""
        )

        # Invariant: fetched == test_address
        if fetched != test_address:
            sig = FailureSignature(
                kind="relation_violation",
                first_party_endpoint="/api/account/address",
                error_type="AddressPersistenceViolation",
                message_norm=normalize_message(
                    f"AddressPersistenceViolation: Expected '{test_address}' after reload, found '{fetched}'"
                ),
            )
            fid = f"finding_B_{hashlib.sha256(sig.message_norm.encode('utf-8')).hexdigest()[:8]}"
            return Finding(
                id=fid,
                oracle_class=OracleClass.B,
                tier=Tier.VERIFIED_VIOLATION,
                signature=sig,
                claim="Saved user address is lost after page reload (B07)",
                steps=[
                    Action(id="r_save_addr", kind=ActionKind.FILL, locator=Locator(label="Shipping Address"), value=test_address),
                    Action(id="r_reload", kind=ActionKind.GOTO, value="/"),
                ],
                confidence=1.0,
                intent_confirmation_needed=True,
            )

        return None

    async def validate(self, world_spec: WorldSpec) -> bool:
        clean_spec = WorldSpec(app_id=world_spec.app, bugs=[])
        world = World(clean_spec)
        with world:
            h = BrowserHarness()
            async with h:
                for _ in range(3):
                    context, page = await h.new_context()
                    violation = await self.run(page, world.url)
                    await context.close()
                    if violation is not None:
                        return False
        return True
