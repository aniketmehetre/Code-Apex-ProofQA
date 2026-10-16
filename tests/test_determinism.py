"""Determinism tests proving identical seeds and levels produce identical Action sequences."""

from __future__ import annotations

from pathlib import Path

import pytest

from proofqa.contracts import WorldSpec
from proofqa.explore.explorer import RuleBasedExplorer
from proofqa.world.manager import World


@pytest.mark.asyncio
@pytest.mark.parametrize("level", ["monkey", "rules"])
async def test_determinism_same_seed_and_level_produce_identical_actions(level: str, tmp_path: Path) -> None:
    """Proves that identical seed and level produce an identical sequence of ActionEvents."""
    seed = 42
    spec = WorldSpec(app_id="shop_twin", bugs=[], seed=seed)

    # Run 1
    world1 = World(spec)
    with world1:
        exp1 = RuleBasedExplorer(
            world=world1,
            budget_steps=6,
            seed=seed,
            level=level,
            output_dir=tmp_path / f"det1_{level}",
        )
        res1 = await exp1.explore()

    # Run 2
    world2 = World(spec)
    with world2:
        exp2 = RuleBasedExplorer(
            world=world2,
            budget_steps=6,
            seed=seed,
            level=level,
            output_dir=tmp_path / f"det2_{level}",
        )
        res2 = await exp2.explore()

    assert res1.steps_executed == res2.steps_executed
    assert len(exp1.action_history) == len(exp2.action_history)

    for i, (act1, act2) in enumerate(zip(exp1.action_history, exp2.action_history)):
        assert act1.kind == act2.kind, f"Step {i}: kind mismatch {act1.kind} != {act2.kind}"
        assert act1.value == act2.value, f"Step {i}: value mismatch {act1.value} != {act2.value}"
        assert act1.locator == act2.locator, f"Step {i}: locator mismatch {act1.locator} != {act2.locator}"
