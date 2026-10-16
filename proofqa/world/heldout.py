"""Held-out bug flags (H01-H05) and extended decoys (D06-D10) for Shop Twin.

Separated strictly from the development bug catalogue (B01-B10).
Evaluated exclusively on held-out evaluation seeds (101-110).
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException


def is_heldout_on(bug_id: str) -> bool:
    """Check if a specific held-out bug flag is active in BUGS environment variable."""
    bugs_env = os.environ.get("BUGS", "")
    if not bugs_env:
        return False
    active = {b.strip().upper() for b in bugs_env.split(",") if b.strip()}
    return bug_id.strip().upper() in active


# ============================================================================
# Held-Out Bugs (H01 - H05)
# ============================================================================

def check_h01_cart_quantity(quantity: int) -> None:
    """H01: POST /api/cart with negative quantity raises HTTP 500."""
    if is_heldout_on("H01") and quantity < 0:
        raise HTTPException(
            status_code=500,
            detail="NegativeQuantityException: Cannot allocate cart buffer with negative item quantity",
        )


def check_h02_search_query(q: str | None) -> None:
    """H02: Search query containing double quote, percent sign, or backslash raises HTTP 500."""
    if is_heldout_on("H02") and q:
        if any(char in q for char in ('"', '%', "\\")):
            raise HTTPException(
                status_code=500,
                detail="DatabaseError: syntax error near unescaped search token",
            )


def check_h03_sort_revert(
    sort_key: str | None,
    session_state: dict[str, Any],
    products: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """H03: Sorting by name fails to restore original ordering after reverting to default."""
    if is_heldout_on("H03"):
        if sort_key in ("name", "name_asc"):
            session_state["h03_sorted_name"] = True
            return sorted(products, key=lambda p: p.get("name", ""))
        elif sort_key in ("", "default", None) and session_state.get("h03_sorted_name"):
            # Bug: Returns products sorted by name instead of restoring ID order
            return sorted(products, key=lambda p: p.get("name", ""))
    elif sort_key in ("name", "name_asc"):
        return sorted(products, key=lambda p: p.get("name", ""))
    return products


def check_h04_profile_save(profile_data: dict[str, Any], session_state: dict[str, Any]) -> None:
    """H04: Saving profile field (display_name/phone) fails to persist on retrieval."""
    if is_heldout_on("H04"):
        # Bug: Suppress persistence of phone and display_name
        session_state["profile_phone"] = None
        session_state["profile_display_name"] = None
    else:
        if "phone" in profile_data:
            session_state["profile_phone"] = profile_data["phone"]
        if "display_name" in profile_data:
            session_state["profile_display_name"] = profile_data["display_name"]


def check_h05_direct_checkout(session_state: dict[str, Any]) -> None:
    """H05: Direct checkout with coupon applied without line item modification raises HTTP 500."""
    if is_heldout_on("H05"):
        has_coupon = bool(session_state.get("applied_coupon"))
        has_removed = bool(session_state.get("removed_item", False))
        if has_coupon and not has_removed:
            raise HTTPException(
                status_code=500,
                detail="NullReferenceException: Direct coupon checkout without line item verification failed",
            )


# ============================================================================
# Extended Decoys (D06 - D10)
# ============================================================================

def apply_d06_equal_price_sort(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """D06: Items with identical price may reorder arbitrarily (benign tie-breaking)."""
    # Deterministic reverse tie-break for equal-price items
    return sorted(products, key=lambda p: (p.get("price", 0), -p.get("id", 0)))


def check_d08_cart_quantity_bounds(quantity: int) -> None:
    """D08: Out-of-bounds quantity returns friendly HTTP 400 instead of 500."""
    if quantity < 0 or quantity > 99:
        if not is_heldout_on("H01"):  # H01 takes precedence when enabled
            raise HTTPException(
                status_code=400,
                detail="BadRequest: Quantity out of allowable range (1-99)",
            )


def check_d10_rate_limit(request_count: int) -> None:
    """D10: Rapid endpoint dispatch returns friendly HTTP 429, never HTTP 5xx."""
    if request_count >= 15:
        raise HTTPException(
            status_code=429,
            detail="TooManyRequests: Friendly rate limit exceeded. Please retry in 1 second.",
        )
