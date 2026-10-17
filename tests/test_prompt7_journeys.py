"""Tests for Prompt 7: Journey planning, mutations, and generic commerce intents."""

from __future__ import annotations

import random

from proofqa.contracts import Action, ActionKind, Locator
from proofqa.explore.journeys import (
    JourneyPlanner,
    mutate_journey,
)


def test_journey_mutations():
    rng = random.Random(42)
    original = ["add_item", "add_item", "apply_code", "checkout"]

    # Generate 10 mutations
    mutations = [mutate_journey(original, rng) for _ in range(10)]
    assert len(mutations) == 10

    # Ensure variations occur
    unique_mutations = {tuple(m) for m in mutations}
    assert len(unique_mutations) > 1


def test_journey_mapping_to_grounded_controls():
    planner = JourneyPlanner(seed=42)

    cands = [
        Action(id="btn_add_1", kind=ActionKind.CLICK, locator=Locator(role="button", name="Add to Cart", testid="add-to-cart-1")),
        Action(id="btn_add_2", kind=ActionKind.CLICK, locator=Locator(role="button", name="Add to Cart", testid="add-to-cart-2")),
        Action(id="btn_remove", kind=ActionKind.CLICK, locator=Locator(role="button", name="Remove item")),
        Action(id="btn_checkout", kind=ActionKind.CLICK, locator=Locator(role="button", name="Proceed to Checkout")),
    ]

    # Map add_item: should return one of the add buttons
    act1 = planner.map_intent_to_action("add_item", cands)
    assert act1 is not None
    assert act1.id in ("btn_add_1", "btn_add_2")

    # Map remove_item: should return remove button
    act2 = planner.map_intent_to_action("remove_item", cands)
    assert act2 is not None
    assert act2.id == "btn_remove"

    # Map checkout: should return checkout button
    act3 = planner.map_intent_to_action("checkout", cands)
    assert act3 is not None
    assert act3.id == "btn_checkout"

    # Unmapped intent should return None without error
    act4 = planner.map_intent_to_action("register", cands)
    assert act4 is None
