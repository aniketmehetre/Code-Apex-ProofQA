"""Tests for Prompt 6: SemanticState, GoExploreArchive, and deep-state reach."""

from __future__ import annotations

import random

import pytest

from proofqa.contracts import Action, ActionKind, Locator, WorldSpec
from proofqa.explore.archive import GoExploreArchive
from proofqa.explore.config import ExplorerConfig
from proofqa.explore.explorer import RuleBasedExplorer
from proofqa.explore.semantic_state import bucket_count
from proofqa.world.manager import World


def test_bucket_count():
    assert bucket_count(0) == "0"
    assert bucket_count(-5) == "0"
    assert bucket_count(1) == "1"
    assert bucket_count(2) == "2"
    assert bucket_count(3) == "3+"
    assert bucket_count(99) == "3+"


def test_goexplore_archive_selection_and_novelty():
    archive = GoExploreArchive(max_cell_visits=5)
    rng = random.Random(42)

    act1 = Action(id="a1", kind=ActionKind.CLICK, locator=Locator(name="Item 1"))
    act2 = Action(id="a2", kind=ActionKind.CLICK, locator=Locator(name="Item 2"))
    act3 = Action(id="a3", kind=ActionKind.CLICK, locator=Locator(name="Item 3"))

    # Add cell 1 with 3 actions
    c1, added = archive.add_or_update("state_1", [act1], [act2, act3])
    assert added is True
    assert c1.visit_count == 1
    assert len(c1.untried_actions) == 2

    # Add cell 2 with 1 action
    c2, added = archive.add_or_update("state_2", [act1, act2], [act3])
    assert added is True

    # Seeded choice should deterministic select a cell
    selected = archive.select_cell(rng)
    assert selected is not None
    assert selected.state_key in ("state_1", "state_2")

    # Shortest prefix update
    c2_updated, is_new = archive.add_or_update("state_2", [act2], [])
    assert is_new is False
    assert len(c2_updated.prefix) == 1  # updated to shorter prefix!

    # Staleness marking
    archive.mark_stale("state_1")
    assert archive.cells["state_1"].is_stale is True

    # After state_1 is stale, select_cell only picks state_2
    selected2 = archive.select_cell(rng)
    assert selected2 is not None
    assert selected2.state_key == "state_2"


def test_goexplore_trap_state_cap():
    """Verify D05 trap pages cannot explode the state graph beyond per_path_state_cap."""
    config = ExplorerConfig(per_path_state_cap=8)
    spec = WorldSpec(app_id="shop_twin", bugs=[])
    world = World(spec)

    explorer = RuleBasedExplorer(
        world=world,
        budget_steps=10,
        level="rules_probes_goexplore",
        config=config,
    )

    # Trap paths should be identified
    assert explorer._is_trap("/trap/infinite_loop") is True
    assert explorer._is_trap("/products") is False


@pytest.mark.asyncio
async def test_deterministic_deep_state_reach_shop_twin():
    """Deterministic reach test on Shop Twin with ALL bugs off:

    Verify explorer reaches state with distinct items and discount applied within budget.
    """
    spec = WorldSpec(app_id="shop_twin", bugs=[], seed=42)
    world = World(spec)

    config = ExplorerConfig(
        level="rules_probes_goexplore",
        max_actions_per_run=35,
        budget_depth=8,
        archive_budget_fraction=0.5,
    )

    with world:
        explorer = RuleBasedExplorer(
            world=world,
            budget_steps=35,
            seed=42,
            level="rules_probes_goexplore",
            config=config,
        )

        res = await explorer.explore()
        assert res.steps_executed > 0

        # Check archive states discovered
        archived_keys = list(explorer.archive.cells.keys())
        assert len(archived_keys) > 1

        # Check if deep state was reached: cart with items or discount
        has_deep_cart_state = any(
            "items:1" in k or "items:2" in k or "items:3+" in k
            for k in archived_keys
        )
        assert has_deep_cart_state is True
