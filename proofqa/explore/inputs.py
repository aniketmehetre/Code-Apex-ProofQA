"""Deterministic form input library and test account generator."""

from __future__ import annotations

import hashlib
from typing import Any

from proofqa.contracts import Locator

DETERMINISTIC_INPUT_LIBRARY = [
    "ValidInput",                         # Valid standard value
    "",                                   # Empty string
    "A" * 1000,                           # Very long string buffer
    "こんにちは 🚀🔥 Verification",          # Unicode and emoji
    "Gamer's ' OR '1'='1",                # Single and double quote characters
    "0",                                  # Zero
    "-1",                                 # Negative value
    "999999999",                          # Huge boundary number
]


def rotate_input(field_name: str, step_index: int) -> str:
    """Rotates deterministically through input boundary classes based on field and step."""
    seed_offset = int(hashlib.md5(field_name.encode("utf-8")).hexdigest()[:4], 16)
    idx = (step_index + seed_offset) % len(DETERMINISTIC_INPUT_LIBRARY)
    return DETERMINISTIC_INPUT_LIBRARY[idx]


def get_field_input(
    locator: Locator | None,
    step_index: int,
    seed: int = 42,
) -> str:
    """Derives a deterministic field input value appropriate for semantic field hints."""
    name_hint = ((locator.name or "") + " " + (locator.label or "")).lower()

    if "password" in name_hint:
        return "Password123!"

    if "email" in name_hint:
        return f"user_{seed}_{step_index}@proofqa-test.invalid"

    if "search" in name_hint:
        search_terms = ["headphones", "keyboard", "Gamer's", "", "mouse", "monitor"]
        return search_terms[step_index % len(search_terms)]

    if "quantity" in name_hint or "qty" in name_hint:
        quantities = ["1", "2", "0", "-1", "99"]
        return quantities[step_index % len(quantities)]

    if "coupon" in name_hint or "code" in name_hint:
        coupons = ["SAVE10", "WELCOME20", "FREESHIP", "INVALID_CODE"]
        return coupons[step_index % len(coupons)]

    if "address" in name_hint or "shipping" in name_hint:
        return "123 Verification Lane, Suite 404"

    return rotate_input(name_hint or "general_field", step_index)


def generate_disposable_account(seed: int, index: int) -> dict[str, Any]:
    """Generates deterministic credentials for automated test account registration."""
    acc_hash = hashlib.sha256(f"{seed}:{index}".encode("utf-8")).hexdigest()[:8]
    return {
        "name": f"Test Agent {acc_hash}",
        "email": f"agent_{acc_hash}@proofqa-test.invalid",
        "password": "ValidPassword123!",
    }
