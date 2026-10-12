"""Metamorphic relation: default sort restoration invariant."""

from __future__ import annotations

import asyncio
import hashlib
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


class SortRestorationRelation(Relation):
    """Sort restoration metamorphic invariant:

    Sorting by price and subsequently returning to default sort MUST restore the initial product permutation.
    """

    name = "sort_restoration_invariant"

    def applies(self, widgets: dict[str, Any]) -> bool:
        return bool(widgets.get("sort_control", False))

    async def _extract_product_titles(self, page: Page) -> list[str]:
        titles = page.locator(".product-title")
        count = await titles.count()
        return [(await titles.nth(i).text_content() or "").strip() for i in range(count)]

    async def run(self, page: Page, world_url: str) -> Finding | None:
        sort_select = page.locator('select[aria-label="Sort products"]')
        if await sort_select.count() == 0:
            return None

        # 1. Record initial permutation on default sort
        initial_titles = await self._extract_product_titles(page)
        if not initial_titles:
            return None

        # 2. Sort by price ascending
        await sort_select.select_option("price_asc")
        await asyncio.sleep(0.5)

        # 3. Restore default sort order
        await sort_select.select_option("")
        await asyncio.sleep(0.5)

        # 4. Record restored permutation
        restored_titles = await self._extract_product_titles(page)

        # Invariant: initial_titles == restored_titles
        if initial_titles != restored_titles:
            sig = FailureSignature(
                kind="relation_violation",
                error_type="SortRestorationViolation",
                message_norm=normalize_message(
                    "SortRestorationViolation: Default product order not restored after switching from price sort"
                ),
            )
            fid = f"finding_B_{hashlib.sha256(sig.message_norm.encode('utf-8')).hexdigest()[:8]}"
            return Finding(
                id=fid,
                oracle_class=OracleClass.B,
                tier=Tier.VERIFIED_VIOLATION,
                signature=sig,
                claim="Default catalog sort order is corrupted after sorting by price and returning to default",
                steps=[
                    Action(id="r_sort_asc", kind=ActionKind.SELECT, locator=Locator(role="combobox", label="Sort by Price"), value="price_asc"),
                    Action(id="r_sort_default", kind=ActionKind.SELECT, locator=Locator(role="combobox", label="Sort by Price"), value=""),
                ],
                confidence=1.0,
                intent_confirmation_needed=True,
            )

        return None

    async def validate(self, world_spec: WorldSpec) -> bool:
        """Validates that this invariant holds on a clean reference world across runs."""
        # Clean world validation
        clean_spec = WorldSpec(app_id=world_spec.app, bugs=[])
        world = World(clean_spec)
        with world:
            h = BrowserHarness()
            async with h:
                for _ in range(3):
                    context, page = await h.new_context()
                    await page.goto(f"{world.url}/", wait_until="networkidle")
                    violation = await self.run(page, world.url)
                    await context.close()
                    if violation is not None:
                        return False
        return True
