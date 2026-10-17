"""Generic intent journeys and mutations for deep CRUD/commerce workflows (Prompt 7)."""

from __future__ import annotations

import random
from typing import Literal

from proofqa.contracts import Action, ActionKind
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
