"""Class D Cross-Layer Consistency Oracle comparing rendered UI facts against API truth."""

from __future__ import annotations

import asyncio
import hashlib
import re
import time
from typing import Any

from playwright.async_api import Page

from proofqa.contracts import (
    Action,
    FailureSignature,
    Finding,
    OracleClass,
    Tier,
    UiFactEvent,
    normalize_message,
)

_PRICE_RE = re.compile(r"\$\s*(\d+(?:\.\d{1,2})?)")


class CrossLayerOracle:
    """Class D oracle enforcing consistency between ground-truth network APIs and rendered UI."""

    def __init__(self, tolerance: float = 0.01, settle_delay_seconds: float = 0.5) -> None:
        self.tolerance = tolerance
        self.settle_delay_seconds = settle_delay_seconds
        self.candidates: list[Finding] = []
        self._seen_signatures: set[str] = set()

    async def extract_ui_facts(self, page: Page) -> dict[str, Any]:
        """Extracts key numerical UI facts (counts, totals, badge values)."""
        facts: dict[str, Any] = {}

        # 1. Cart badge count
        try:
            badge = page.locator('[data-testid="cart-badge"]')
            if await badge.count() > 0 and await badge.first.is_visible():
                text = (await badge.first.text_content() or "").strip()
                digits = re.findall(r"\d+", text)
                if digits:
                    facts["cart_badge_count"] = int(digits[0])
        except Exception:
            pass

        # 2. Rendered catalog product count
        try:
            pcount = page.locator('[data-testid="product-count"]')
            if await pcount.count() > 0 and await pcount.first.is_visible():
                text = (await pcount.first.text_content() or "").strip()
                digits = re.findall(r"\d+", text)
                if digits:
                    facts["rendered_product_count"] = int(digits[0])
        except Exception:
            pass

        # 3. Cart Total
        try:
            total_el = page.locator('[data-testid="cart-total"]')
            if await total_el.count() > 0 and await total_el.first.is_visible():
                text = (await total_el.first.text_content() or "").strip()
                match = _PRICE_RE.search(text)
                if match:
                    facts["cart_total"] = float(match.group(1))
        except Exception:
            pass

        # 4. Cart items table row count
        try:
            rows = page.locator("tbody tr")
            if await rows.count() > 0:
                facts["cart_rendered_items_count"] = await rows.count()
        except Exception:
            pass

        return facts

    async def verify_consistency(
        self,
        page: Page,
        api_responses: dict[str, Any],
        action_prefix: list[Action],
    ) -> list[tuple[UiFactEvent, Finding | None]]:
        """Compares extracted UI facts against latest relevant JSON API responses."""
        ui_facts = await self.extract_ui_facts(page)
        results: list[tuple[UiFactEvent, Finding | None]] = []

        # Check 1: Cart Badge Count vs API cart item_count / items length
        cart_data = None
        for k in reversed(list(api_responses.keys())):
            if k.startswith("/api/cart"):
                cart_data = api_responses[k]
                break

        if "cart_badge_count" in ui_facts and cart_data is not None:
            api_count = cart_data.get("item_count")
            if api_count is None and "items" in cart_data:
                api_count = sum(it.get("quantity", 1) for it in cart_data["items"])

            if api_count is not None:
                ui_val = ui_facts["cart_badge_count"]
                mismatch = ui_val != api_count

                if mismatch:
                    # Settle delay: wait and re-extract to rule out transient animation delays
                    await asyncio.sleep(self.settle_delay_seconds)
                    recheck_facts = await self.extract_ui_facts(page)
                    ui_val = recheck_facts.get("cart_badge_count", ui_val)
                    mismatch = ui_val != api_count

                event = UiFactEvent(
                    label="cart_badge_count",
                    ui_value=ui_val,
                    api_value=api_count,
                    api_ref="/api/cart",
                    timestamp_ms=time.time() * 1000,
                )

                finding = None
                if mismatch:
                    sig = FailureSignature(
                        kind="ui_mismatch",
                        first_party_endpoint="/api/cart",
                        error_type="CrossLayerMismatch",
                        message_norm=normalize_message(
                            f"CrossLayerMismatch: cart_badge_count UI shows {ui_val} but API item_count is {api_count}"
                        ),
                    )
                    finding = self._create_finding(
                        sig,
                        f"Cart badge displays {ui_val} but API truth item_count is {api_count}",
                        action_prefix,
                    )

                results.append((event, finding))

        # Check 2: Cart Total vs API cart total (B04 detection)
        if "cart_total" in ui_facts and cart_data is not None:
            subtotal = float(cart_data.get("subtotal", 0.0))
            discount = float(cart_data.get("discount", 0.0))
            expected_total = round(max(0.0, subtotal - discount), 2)
            api_total = float(cart_data.get("total", subtotal))
            ui_val = ui_facts["cart_total"]

            mismatch = (abs(ui_val - expected_total) > self.tolerance and discount > 0) or (abs(ui_val - api_total) > self.tolerance)

            if mismatch:
                await asyncio.sleep(self.settle_delay_seconds)
                recheck_facts = await self.extract_ui_facts(page)
                ui_val = recheck_facts.get("cart_total", ui_val)
                mismatch = (abs(ui_val - expected_total) > self.tolerance and discount > 0) or (abs(ui_val - api_total) > self.tolerance)

            event = UiFactEvent(
                label="cart_total",
                ui_value=ui_val,
                api_value=expected_total if discount > 0 else api_total,
                api_ref="/api/cart",
                timestamp_ms=time.time() * 1000,
            )

            finding = None
            if mismatch:
                sig = FailureSignature(
                    kind="ui_mismatch",
                    first_party_endpoint="/api/cart",
                    error_type="CrossLayerMismatch",
                    message_norm=normalize_message(
                        f"CrossLayerMismatch: cart_total UI displays ${ui_val:.2f} but truth total is ${expected_total:.2f}"
                    ),
                )
                finding = self._create_finding(
                    sig,
                    f"Cart displayed total (${ui_val:.2f}) ignores discount (truth: ${expected_total:.2f})",
                    action_prefix,
                    )

                results.append((event, finding))

        # Check 3: Product Count vs API products total
        if "rendered_product_count" in ui_facts and "/api/products" in api_responses:
            prod_data = api_responses["/api/products"]
            api_total_products = prod_data.get("total")
            if api_total_products is not None:
                ui_val = ui_facts["rendered_product_count"]
                mismatch = ui_val != api_total_products
                event = UiFactEvent(
                    label="rendered_product_count",
                    ui_value=ui_val,
                    api_value=api_total_products,
                    api_ref="/api/products",
                    timestamp_ms=time.time() * 1000,
                )
                results.append((event, None))

        return results

    def _create_finding(
        self,
        sig: FailureSignature,
        claim: str,
        action_prefix: list[Action],
    ) -> Finding | None:
        sig_key = f"{sig.kind}:{sig.first_party_endpoint}:{sig.message_norm}"
        if sig_key in self._seen_signatures:
            return None
        self._seen_signatures.add(sig_key)

        finding_id = f"finding_D_{hashlib.sha256(sig_key.encode('utf-8')).hexdigest()[:8]}"
        finding = Finding(
            id=finding_id,
            oracle_class=OracleClass.D,
            tier=Tier.SUSPECTED,
            signature=sig,
            claim=claim,
            steps=list(action_prefix),
            confidence=1.0,
            intent_confirmation_needed=False,
        )
        self.candidates.append(finding)
        return finding
