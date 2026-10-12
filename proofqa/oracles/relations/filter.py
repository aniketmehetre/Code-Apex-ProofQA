"""Metamorphic relation: category filter subset and pagination purity invariant."""

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


class CategoryFilterRelation(Relation):
    """Category filter subset invariant:

    Selecting a category MUST restrict all returned items on page 1 and paginated page 2
    strictly to that category.
    """

    name = "category_filter_purity_invariant"

    def applies(self, widgets: dict[str, Any]) -> bool:
        return bool(widgets.get("category_filter", False)) and bool(widgets.get("paginator", False))

    async def run(self, page: Page, world_url: str) -> Finding | None:
        cat_select = page.locator('select[aria-label="Filter by Category"]')
        if await cat_select.count() == 0:
            return None

        # 1. Filter by Electronics
        await cat_select.select_option("Electronics")
        await asyncio.sleep(0.3)

        # 2. Click page 2 button in pagination navigation
        page_2_btn = page.locator('button[aria-label="Page 2"], button.page-btn:has-text("2")')
        if await page_2_btn.count() == 0 or not await page_2_btn.first.is_visible():
            return None

        await page_2_btn.first.click()
        await asyncio.sleep(0.5)

        # 3. Inspect rendered product category tags on page 2
        tags = page.locator(".product-category-tag")
        count = await tags.count()
        rendered_categories = [(await tags.nth(i).text_content() or "").strip() for i in range(count)]

        # Invariant: Every tag on page 2 must equal "Electronics"
        leakage = [c for c in rendered_categories if c and c != "Electronics"]
        if leakage:
            sig = FailureSignature(
                kind="relation_violation",
                error_type="CategoryFilterLeakageViolation",
                message_norm=normalize_message(
                    f"CategoryFilterLeakageViolation: Page 2 of category filter leaked {len(leakage)} items from other categories"
                ),
            )
            fid = f"finding_B_{hashlib.sha256(sig.message_norm.encode('utf-8')).hexdigest()[:8]}"
            return Finding(
                id=fid,
                oracle_class=OracleClass.B,
                tier=Tier.VERIFIED_VIOLATION,
                signature=sig,
                claim="Category filter on page 2 returns items from other categories (B06)",
                steps=[
                    Action(id="r_select_cat", kind=ActionKind.SELECT, locator=Locator(role="combobox", label="Filter by Category"), value="Electronics"),
                    Action(id="r_page_2", kind=ActionKind.CLICK, locator=Locator(role="button", label="Go to page 2")),
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
                    await page.goto(f"{world.url}/", wait_until="networkidle")
                    violation = await self.run(page, world.url)
                    await context.close()
                    if violation is not None:
                        return False
        return True
