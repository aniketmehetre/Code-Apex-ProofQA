"""Reachability specifications and predicates evaluating server-side request logs.

Determines whether the execution reached the precondition / trigger state
for each bug in the catalogue, independently of whether ProofQA's oracles detected it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ReachSpec:
    """Reachability predicate for a bug based strictly on server-side request logs."""

    bug_id: str
    description: str
    predicate: Callable[[list[dict[str, Any]]], bool]

    def is_reached(self, request_log: list[dict[str, Any]]) -> bool:
        return self.predicate(request_log)


def _check_b01(log: list[dict[str, Any]]) -> bool:
    """B01: POST /api/cart with quantity == 0."""
    for req in log:
        if req.get("method") == "POST" and req.get("path") == "/api/cart":
            body = req.get("body")
            if isinstance(body, dict):
                qty = body.get("quantity")
                if qty == 0 or qty == "0":
                    return True
    return False


def _check_b02(log: list[dict[str, Any]]) -> bool:
    """B02: Coupon applied, item removed, checkout called."""
    has_cart_add = False
    has_coupon = False
    has_item_removed = False

    for req in log:
        m = req.get("method")
        p = req.get("path", "")

        if m == "POST" and p == "/api/cart":
            has_cart_add = True
        elif m == "POST" and "/api/coupons/apply" in p:
            if has_cart_add:
                has_coupon = True
        elif (m == "DELETE" and "/api/cart/" in p) or (m == "PATCH" and "/api/cart/" in p and req.get("body", {}).get("quantity") == 0):
            if has_coupon:
                has_item_removed = True
        elif m == "POST" and p == "/api/checkout":
            if has_item_removed:
                return True
    return False


def _check_b03(log: list[dict[str, Any]]) -> bool:
    """B03: Add item, remove item, fetch cart badge."""
    has_cart_add = False
    has_remove = False

    for req in log:
        m = req.get("method")
        p = req.get("path", "")

        if m == "POST" and p == "/api/cart":
            has_cart_add = True
        elif m == "DELETE" and "/api/cart/" in p:
            if has_cart_add:
                has_remove = True
        elif m == "GET" and p == "/api/cart":
            if has_remove:
                return True
    return False


def _check_b04(log: list[dict[str, Any]]) -> bool:
    """B04: Add item, apply coupon, fetch cart."""
    has_cart_add = False
    has_coupon = False

    for req in log:
        m = req.get("method")
        p = req.get("path", "")

        if m == "POST" and p == "/api/cart":
            has_cart_add = True
        elif m == "POST" and "/api/coupons/apply" in p:
            if has_cart_add:
                has_coupon = True
        elif m == "GET" and p == "/api/cart":
            if has_coupon:
                return True
    return False


def _check_b05(log: list[dict[str, Any]]) -> bool:
    """B05: Products sorted by price_asc, then reverted to default sort."""
    has_price_sort = False

    for req in log:
        if req.get("method") == "GET" and req.get("path") == "/api/products":
            q = req.get("query", {})
            sort_val = q.get("sort")
            if sort_val == "price_asc":
                has_price_sort = True
            elif has_price_sort and (not sort_val or sort_val in ("", "default")):
                return True
    return False


def _check_b06(log: list[dict[str, Any]]) -> bool:
    """B06: Filter by category on page 2."""
    for req in log:
        if req.get("method") == "GET" and req.get("path") == "/api/products":
            q = req.get("query", {})
            page_val = str(q.get("page", "1"))
            cat_val = q.get("category")
            if cat_val and page_val == "2":
                return True
    return False


def _check_b07(log: list[dict[str, Any]]) -> bool:
    """B07: User registered/logged in, saved address, then retrieved address."""
    has_auth = False
    has_put_address = False

    for req in log:
        m = req.get("method")
        p = req.get("path", "")

        if m == "POST" and (p in ("/api/register", "/api/login")):
            if req.get("status", 0) in (200, 201):
                has_auth = True
        elif m == "PUT" and p == "/api/account/address":
            if has_auth or req.get("status", 0) in (200, 204):
                has_put_address = True
        elif m == "GET" and p == "/api/account/address":
            if has_put_address:
                return True
    return False


def _check_b08(log: list[dict[str, Any]]) -> bool:
    """B08: Register user with password length 4 (or under 8)."""
    for req in log:
        if req.get("method") == "POST" and req.get("path") == "/api/register":
            body = req.get("body")
            if isinstance(body, dict):
                pw = body.get("password")
                if isinstance(pw, str) and 1 <= len(pw) < 8:
                    return True
    return False


def _check_b09(log: list[dict[str, Any]]) -> bool:
    """B09: Repeated rapid add to cart requests (burst contention)."""
    cart_posts = 0
    for req in log:
        if req.get("method") == "POST" and req.get("path") == "/api/cart":
            cart_posts += 1
            if cart_posts >= 3:
                return True
    return False


def _check_b10(log: list[dict[str, Any]]) -> bool:
    """B10: Search query with unescaped single quote."""
    for req in log:
        if req.get("method") == "GET" and req.get("path") == "/api/products":
            q = req.get("query", {})
            query_str = q.get("q", "")
            if "'" in query_str:
                return True
    return False


def _check_h01(log: list[dict[str, Any]]) -> bool:
    """H01: POST /api/cart with quantity < 0."""
    for req in log:
        if req.get("method") == "POST" and req.get("path") == "/api/cart":
            body = req.get("body")
            if isinstance(body, dict):
                qty = body.get("quantity")
                try:
                    if int(qty) < 0:
                        return True
                except (ValueError, TypeError):
                    pass
    return False


def _check_h02(log: list[dict[str, Any]]) -> bool:
    """H02: GET /api/products with double quote, percent sign, or backslash in q."""
    for req in log:
        if req.get("method") == "GET" and req.get("path") == "/api/products":
            q = req.get("query", {})
            query_str = q.get("q", "")
            if any(char in query_str for char in ('"', '%', "\\")):
                return True
    return False


def _check_h03(log: list[dict[str, Any]]) -> bool:
    """H03: Products sorted by name then reverted to default sort."""
    has_name_sort = False
    for req in log:
        if req.get("method") == "GET" and req.get("path") == "/api/products":
            q = req.get("query", {})
            sort_val = q.get("sort")
            if sort_val in ("name", "name_asc"):
                has_name_sort = True
            elif has_name_sort and (not sort_val or sort_val in ("", "default")):
                return True
    return False


def _check_h04(log: list[dict[str, Any]]) -> bool:
    """H04: PUT /api/account/profile with phone or display_name, then GET /api/account/profile."""
    has_put = False
    for req in log:
        m = req.get("method")
        p = req.get("path", "")
        if m == "PUT" and p == "/api/account/profile":
            body = req.get("body", {})
            if isinstance(body, dict) and ("phone" in body or "display_name" in body):
                has_put = True
        elif m == "GET" and p == "/api/account/profile":
            if has_put:
                return True
    return False


def _check_h05(log: list[dict[str, Any]]) -> bool:
    """H05: Add to cart, apply coupon, checkout directly without item removal."""
    has_cart_add = False
    has_coupon = False
    has_removal = False
    for req in log:
        m = req.get("method")
        p = req.get("path", "")
        if m == "POST" and p == "/api/cart":
            has_cart_add = True
        elif m == "POST" and "/api/coupons/apply" in p:
            if has_cart_add:
                has_coupon = True
        elif (m == "DELETE" and "/api/cart/" in p) or (m == "PATCH" and "/api/cart/" in p):
            has_removal = True
        elif m == "POST" and p == "/api/checkout":
            if has_coupon and not has_removal:
                return True
    return False


REACH_SPECS: dict[str, ReachSpec] = {
    "B01": ReachSpec("B01", "POST /api/cart with quantity 0", _check_b01),
    "B02": ReachSpec("B02", "Coupon applied, item removed, checkout called", _check_b02),
    "B03": ReachSpec("B03", "Add item, remove item, fetch cart badge", _check_b03),
    "B04": ReachSpec("B04", "Add item, apply coupon, fetch cart", _check_b04),
    "B05": ReachSpec("B05", "Sort by price_asc then revert to default", _check_b05),
    "B06": ReachSpec("B06", "Filter by category on page 2", _check_b06),
    "B07": ReachSpec("B07", "Authenticate, PUT address, GET address", _check_b07),
    "B08": ReachSpec("B08", "POST /api/register with 4-char password", _check_b08),
    "B09": ReachSpec("B09", "Repeated add to cart requests (>=3)", _check_b09),
    "B10": ReachSpec("B10", "GET /api/products with single quote in q", _check_b10),
    "H01": ReachSpec("H01", "POST /api/cart with negative quantity", _check_h01),
    "H02": ReachSpec("H02", "GET /api/products with quote, percent, or backslash in q", _check_h02),
    "H03": ReachSpec("H03", "Sort by name then revert to default", _check_h03),
    "H04": ReachSpec("H04", "PUT profile phone/name, then GET profile", _check_h04),
    "H05": ReachSpec("H05", "Cart add, coupon apply, checkout directly", _check_h05),
}


def is_bug_reached(bug_id: str, request_log: list[dict[str, Any]]) -> bool:
    """Evaluates whether the trigger condition for bug_id was reached in request_log."""
    spec = REACH_SPECS.get(bug_id.upper())
    if not spec:
        return False
    return spec.is_reached(request_log)

