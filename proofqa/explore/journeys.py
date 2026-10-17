"""Generic intent journeys and mutations for deep CRUD/commerce workflows (Prompt 7)."""

from __future__ import annotations

import random
from typing import Literal

from proofqa.contracts import Action, ActionKind, Locator
from proofqa.explore.grounding import ground_action

IntentKind = Literal[
    "add_item",
    "remove_item",
    "apply_code",
    "clear_code",
    "checkout",
    "register",
    "login",
    "update_profile",
    "search",
    "sort",
    "filter",
    "paginate",
]

_INTENT_KEYWORDS: dict[IntentKind, list[str]] = {
    "add_item": ["add to cart", "add item", "buy now", "modal-add-to-cart", "add"],
    "remove_item": ["remove", "delete", "trash", "remove-item", "clear"],
    "apply_code": ["apply", "apply coupon", "redeem", "promo", "coupon"],
    "clear_code": ["clear", "remove coupon", "cancel"],
    "checkout": ["checkout", "proceed to checkout", "place order", "shipping & checkout"],
    "register": ["register", "sign up", "create account"],
    "login": ["sign in", "login", "log in"],
    "update_profile": ["save", "update profile", "save changes", "save address"],
    "search": ["search", "find"],
    "sort": ["sort", "order by", "sort by"],
    "filter": ["filter", "category", "all categories"],
    "paginate": ["next", "previous", "page"],
}

_INVERSES: dict[IntentKind, IntentKind] = {
    "add_item": "remove_item",
    "apply_code": "clear_code",
}

SEED_JOURNEYS: list[list[IntentKind]] = [
    ["add_item", "add_item", "apply_code", "checkout"],
    ["add_item", "apply_code", "checkout"],
    ["register", "login", "update_profile"],
    ["search", "sort", "filter", "paginate"],
]


def mutate_journey(journey: list[IntentKind], rng: random.Random) -> list[IntentKind]:
    """Applies a single deterministic mutation: delete, swap, repeat, or insert inverse."""
    if not journey:
        return ["add_item"]

    mutated = list(journey)
    mutation_type = rng.choice(["delete", "swap", "repeat", "insert_inverse"])

    if mutation_type == "delete" and len(mutated) > 2:
        idx = rng.randrange(len(mutated))
        mutated.pop(idx)

    elif mutation_type == "swap" and len(mutated) >= 2:
        idx = rng.randrange(len(mutated) - 1)
        mutated[idx], mutated[idx + 1] = mutated[idx + 1], mutated[idx]

    elif mutation_type == "repeat":
        idx = rng.randrange(len(mutated))
        mutated.insert(idx, mutated[idx])

    elif mutation_type == "insert_inverse":
        # Find any step with an inverse
        cands = [i for i, step in enumerate(mutated) if step in _INVERSES]
        if cands:
            i = rng.choice(cands)
            mutated.insert(i + 1, _INVERSES[mutated[i]])

    return mutated


class JourneyPlanner:
    """Plans and executes generic commerce/CRUD journeys through grounded actions."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = random.Random(seed)
        self.used_controls: set[str] = set()

    def map_intent_to_action(
        self,
        intent: IntentKind,
        grounded_controls: list[Action],
        token_pool: set[str] | None = None,
    ) -> Action | None:
        """Maps high-level intent to a matching grounded control using docs/recall/lexicon.md."""
        keywords = _INTENT_KEYWORDS.get(intent, [])
        matching_actions: list[Action] = []

        for act in grounded_controls:
            loc = act.locator
            if not loc:
                continue
            text = " ".join(filter(None, [loc.name, loc.label, loc.testid, loc.role])).lower()
            if any(kw in text for kw in keywords):
                matching_actions.append(act)

        if not matching_actions:
            # If navigating between views (e.g. cart or checkout) is needed
            if intent in ("checkout", "apply_code", "remove_item"):
                # Check if a Cart link or button is present
                for act in grounded_controls:
                    loc = act.locator
                    if loc and ("cart" in (loc.name or "").lower() or "cart" in (loc.label or "").lower()):
                        return ground_action(act, grounded_controls)
            return None

        # Intent-specific specialization
        if intent == "add_item":
            # Prefer an item button not yet used
            fresh = [a for a in matching_actions if a.id not in self.used_controls]
            chosen = self.rng.choice(fresh) if fresh else self.rng.choice(matching_actions)
            self.used_controls.add(chosen.id)
            return ground_action(chosen, grounded_controls)

        elif intent == "apply_code":
            # If an input field is present, fill with token first
            promo_inputs = [
                a for a in grounded_controls
                if a.kind == ActionKind.FILL and any(k in (getattr(a.locator, "label", None) or "").lower() for k in ["coupon", "promo", "code"])
            ]
            if promo_inputs:
                target_input = promo_inputs[0]
                token = next(iter(token_pool)) if token_pool else "SAVE10"
                fill_act = Action(
                    id=target_input.id,
                    kind=ActionKind.FILL,
                    locator=target_input.locator,
                    value=token,
                )
                return ground_action(fill_act, grounded_controls)
            chosen = self.rng.choice(matching_actions)
            return ground_action(chosen, grounded_controls)

        else:
            chosen = self.rng.choice(matching_actions)
            self.used_controls.add(chosen.id)
            return ground_action(chosen, grounded_controls)


def get_canonical_journeys(token: str = "SAVE10", seed: int = 42) -> list[tuple[str, list[Action]]]:
    """Canonical commerce journeys based on docs/recall/lexicon.md."""
    return [
        (
            "search_injection",
            [
                Action(id="j_root_search", kind=ActionKind.GOTO, value="/"),
                Action(id="j_search_quote", kind=ActionKind.FILL, locator=Locator(role="searchbox", name="Search products", label="Search products"), value="'"),
                Action(id="j_search_submit", kind=ActionKind.CLICK, locator=Locator(role="button", name="Search", label="Submit Search")),
            ],
        ),
        (
            "concurrency_burst_cart",
            [
                Action(id="j_root_burst", kind=ActionKind.GOTO, value="/"),
                Action(id="j_burst_cart", kind=ActionKind.CLICK, locator=Locator(role="button", name="Add to Cart"), burst=6),
            ],
        ),
        (
            "sort_reversion",
            [
                Action(id="j_root_sort", kind=ActionKind.GOTO, value="/"),
                Action(id="j_sort_asc", kind=ActionKind.SELECT, locator=Locator(role="combobox", name="Sort products", label="Sort products"), value="price_asc"),
                Action(id="j_sort_def", kind=ActionKind.SELECT, locator=Locator(role="combobox", name="Sort products", label="Sort products"), value=""),
            ],
        ),
        (
            "filter_pagination",
            [
                Action(id="j_root_filter", kind=ActionKind.GOTO, value="/"),
                Action(id="j_filter_cat", kind=ActionKind.SELECT, locator=Locator(role="combobox", name="Filter by Category", label="Filter by Category"), value="Electronics"),
                Action(id="j_page_2", kind=ActionKind.CLICK, locator=Locator(role="button", name="Page 2", label="Page 2")),
            ],
        ),
        (
            "cart_checkout",
            [
                Action(id="j_root_checkout", kind=ActionKind.GOTO, value="/"),
                Action(id="j_add_1", kind=ActionKind.CLICK, locator=Locator(role="button", name="Add to Cart")),
                Action(id="j_add_2", kind=ActionKind.CLICK, locator=Locator(role="button", name="Add to Cart")),
                Action(id="j_add_3", kind=ActionKind.CLICK, locator=Locator(role="button", name="Add to Cart")),
                Action(id="j_view_cart", kind=ActionKind.CLICK, locator=Locator(role="button", name="View Shopping Cart", label="View Shopping Cart")),
                Action(id="j_fill_coupon", kind=ActionKind.FILL, locator=Locator(role="textbox", label="Coupon Code", name="Coupon Code"), value=token),
                Action(id="j_apply_coupon", kind=ActionKind.CLICK, locator=Locator(role="button", name="Apply", label="Apply Coupon")),
                Action(id="j_remove_item", kind=ActionKind.CLICK, locator=Locator(role="button", name="Remove")),
                Action(id="j_proceed_checkout", kind=ActionKind.CLICK, locator=Locator(role="button", name="Proceed to Checkout", label="Proceed to Checkout")),
                Action(id="j_fill_addr", kind=ActionKind.FILL, locator=Locator(role="textbox", name="Shipping Address", label="Shipping Address"), value="123 Test St"),
                Action(id="j_place_order", kind=ActionKind.CLICK, locator=Locator(role="button", name="Place Order", label="Place Order")),
            ],
        ),
        (
            "weak_password_registration",
            [
                Action(id="j_root_reg", kind=ActionKind.GOTO, value="/"),
                Action(id="j_nav_about", kind=ActionKind.CLICK, locator=Locator(role="button", name="About")),
                Action(id="j_auth_signin", kind=ActionKind.CLICK, locator=Locator(role="button", name="Sign In", label="Sign In")),
                Action(id="j_auth_signup", kind=ActionKind.CLICK, locator=Locator(role="button", name="Sign up here")),
                Action(id="j_fill_name", kind=ActionKind.FILL, locator=Locator(role="textbox", name="Full Name", label="Full Name"), value="Weak User"),
                Action(id="j_fill_email", kind=ActionKind.FILL, locator=Locator(role="textbox", name="Email Address", label="Email Address"), value=f"weak_{seed}_{random.randint(100, 999)}@example.com"),
                Action(id="j_fill_pw", kind=ActionKind.FILL, locator=Locator(role="textbox", name="Password", label="Password"), value="1234"),
                Action(id="j_click_reg", kind=ActionKind.CLICK, locator=Locator(role="button", name="Register", label="Register")),
            ],
        ),
        (
            "zero_quantity_cart",
            [
                Action(id="j_root_zero", kind=ActionKind.GOTO, value="/"),
                Action(id="j_click_prod", kind=ActionKind.CLICK, locator=Locator(role="heading", css_fallback=".product-title")),
                Action(id="j_zero_qty", kind=ActionKind.FILL, locator=Locator(role="spinbutton", name="Quantity", label="Quantity"), value="0"),
                Action(id="j_confirm_zero_cart", kind=ActionKind.CLICK, locator=Locator(role="button", name="Add to Cart", testid="modal-add-to-cart", label="Confirm Add to Cart")),
            ],
        ),
        (
            "cart_badge_inspection",
            [
                Action(id="j_root_badge", kind=ActionKind.GOTO, value="/"),
                Action(id="j_add_item", kind=ActionKind.CLICK, locator=Locator(role="button", name="Add to Cart")),
                Action(id="j_view_cart_2", kind=ActionKind.CLICK, locator=Locator(role="button", name="View Shopping Cart", label="View Shopping Cart")),
                Action(id="j_remove_item_2", kind=ActionKind.CLICK, locator=Locator(role="button", name="Remove")),
            ],
        ),
        (
            "cart_coupon_discount",
            [
                Action(id="j_root_coupon", kind=ActionKind.GOTO, value="/"),
                Action(id="j_add_item_3", kind=ActionKind.CLICK, locator=Locator(role="button", name="Add to Cart")),
                Action(id="j_view_cart_3", kind=ActionKind.CLICK, locator=Locator(role="button", name="View Shopping Cart", label="View Shopping Cart")),
                Action(id="j_fill_coupon_3", kind=ActionKind.FILL, locator=Locator(role="textbox", label="Coupon Code", name="Coupon Code"), value=token),
                Action(id="j_apply_coupon_3", kind=ActionKind.CLICK, locator=Locator(role="button", name="Apply", label="Apply Coupon")),
            ],
        ),
    ]
