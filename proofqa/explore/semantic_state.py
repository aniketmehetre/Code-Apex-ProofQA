"""SemanticState: coarse generic state abstraction for Go-Explore (Prompt 6)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse

from playwright.async_api import Page

from proofqa.contracts import StateFingerprint

_DISCOUNT_KEY_RE = re.compile(r"coupon|promo|discount|voucher", re.IGNORECASE)
_D04_VOLATILE_KEYWORDS = {"Special Offer", "Deal of the day", "Save up to", "Exclusive Promo", "Flash Sale"}


def bucket_count(n: int) -> str:
    """Coarse generic bucketing: 0, 1, 2, 3+."""
    if n <= 0:
        return "0"
    if n == 1:
        return "1"
    if n == 2:
        return "2"
    return "3+"


@dataclass(frozen=True)
class SemanticState:
    """Coarse semantic state key avoiding state explosion while preserving deep state distinctions."""

    path: str
    query_params: str
    aria_hash: str
    badge_bucket: str
    array_len_bucket: str
    line_item_bucket: str
    has_discount: bool
    auth_state: str

    @property
    def key(self) -> str:
        return (
            f"{self.path}?{self.query_params}|"
            f"aria:{self.aria_hash}|"
            f"badge:{self.badge_bucket}|"
            f"arr:{self.array_len_bucket}|"
            f"items:{self.line_item_bucket}|"
            f"promo:{1 if self.has_discount else 0}|"
            f"auth:{self.auth_state}"
        )


async def compute_semantic_state(
    page: Page,
    fp: StateFingerprint,
    last_api_responses: dict[str, Any] | None = None,
    volatile_mask: set[str] | None = None,
) -> SemanticState:
    """Derives a generic SemanticState from page URL, ARIA snapshot, and recent API responses."""
    parsed = urlparse(page.url)
    path = parsed.path or "/"

    # 1. State query params (page, sort, filter, category, q)
    raw_query = parse_qs(parsed.query)
    preserved_keys = ["page", "sort", "filter", "category", "q"]
    sorted_pairs = []
    for k in sorted(preserved_keys):
        if k in raw_query and raw_query[k]:
            sorted_pairs.append(f"{k}={raw_query[k][0]}")
    query_params = "&".join(sorted_pairs)

    # 2. ARIA hash with D04 banner masking
    mask = set(_D04_VOLATILE_KEYWORDS)
    if volatile_mask:
        mask.update(volatile_mask)

    try:
        raw_aria = await page.aria_snapshot()
    except Exception:
        raw_aria = ""

    lines = []
    for line in (raw_aria or "").splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        if any(v.lower() in cleaned.lower() for v in mask):
            lines.append("<MASKED_BANNER>")
        else:
            lines.append(cleaned)
    normalized_aria = "\n".join(lines)
    aria_hash = hashlib.sha256(normalized_aria.encode("utf-8")).hexdigest()[:12]

    # 3. Numeric badge count from DOM or API
    badge_val = 0
    try:
        badge_el = await page.query_selector("[data-testid='cart-badge'], .badge, header span")
        if badge_el:
            txt = (await badge_el.text_content() or "").strip()
            digits = re.findall(r"\d+", txt)
            if digits:
                badge_val = int(digits[0])
    except Exception:
        pass

    # 4. API inspection for array lengths, line items, and discounts
    api_responses = last_api_responses or {}
    max_arr_len = 0
    line_item_count = 0
    has_discount = False

    for endpoint, data in api_responses.items():
        if not isinstance(data, dict):
            continue

        # Look for cart items or generic items list
        items = data.get("items")
        if items is None and isinstance(data.get("cart"), dict):
            items = data["cart"].get("items")

        if isinstance(items, list):
            max_arr_len = max(max_arr_len, len(items))
            # If endpoint is cart-related, count distinct items
            if "cart" in endpoint:
                line_item_count = len(items)

    # Fallback to badge count if API items not yet polled
    if line_item_count == 0 and badge_val > 0:
        line_item_count = badge_val

        # Check for discount / promo keys
        for k, v in data.items():
            if _DISCOUNT_KEY_RE.search(k):
                if v and v not in (0, 0.0, "0", False, "null"):
                    has_discount = True
            if isinstance(v, dict):
                for sub_k, sub_v in v.items():
                    if _DISCOUNT_KEY_RE.search(sub_k) and sub_v and sub_v not in (0, 0.0, "0", False, "null"):
                        has_discount = True

    # Check DOM text for discount as well
    if not has_discount:
        try:
            body_txt = await page.inner_text("body")
            if any(term in body_txt for term in ("Discount (SAVE10)", "Coupon applied", "10% discount", "SAVE10 applied")):
                has_discount = True
        except Exception:
            pass

    # 5. Auth state (cookies, localStorage token, or account data)
    auth_state = "anon"
    try:
        storage = await page.evaluate("() => ({ ...localStorage })")
        if any("token" in k.lower() or "auth" in k.lower() or "user" in k.lower() for k in storage):
            auth_state = "auth"
    except Exception:
        pass

    return SemanticState(
        path=path,
        query_params=query_params,
        aria_hash=aria_hash,
        badge_bucket=bucket_count(badge_val),
        array_len_bucket=bucket_count(max_arr_len),
        line_item_bucket=bucket_count(line_item_count),
        has_discount=has_discount,
        auth_state=auth_state,
    )
