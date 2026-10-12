"""Acceptance tests for RuleBasedExplorer, loop avoidance, and state graph persistence."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from proofqa.contracts import WorldSpec
from proofqa.explore import RuleBasedExplorer
from proofqa.world import World


@pytest.mark.asyncio
async def test_clean_twin_exploration_and_coverage(tmp_path: Path) -> None:
    spec = WorldSpec(app_id="shop_twin", bugs=[])
    world = World(spec)

    with world:
        explorer = RuleBasedExplorer(
            world=world,
            budget_steps=12,
            budget_depth=4,
            seed=42,
            output_dir=tmp_path / "exp_1",
            sqlite_path=tmp_path / "exp_1" / "graph.db",
        )
        res = await explorer.explore()

        # Acceptance: Coverage (states and edges) is reported
        assert res.steps_executed > 0
        assert res.coverage["states_count"] >= 2
        assert res.coverage["edges_count"] >= 1
        assert "/" in res.distinct_urls

        # Acceptance: Tape file recorded
        assert res.tape_path.exists()
        assert res.tape_path.stat().st_size > 0

        # Acceptance: SQLite persistence verified
        with sqlite3.connect(tmp_path / "exp_1" / "graph.db") as conn:
            states_row = conn.execute("SELECT count(*) FROM states").fetchone()[0]
            transitions_row = conn.execute("SELECT count(*) FROM transitions").fetchone()[0]
            assert states_row >= 2
            assert transitions_row >= 1


@pytest.mark.asyncio
async def test_deterministic_walk_same_seed(tmp_path: Path) -> None:
    spec = WorldSpec(app_id="shop_twin", bugs=[])

    # Run 1
    world1 = World(spec)
    with world1:
        explorer1 = RuleBasedExplorer(
            world=world1,
            budget_steps=6,
            seed=123,
            output_dir=tmp_path / "run_1",
        )
        res1 = await explorer1.explore()

    # Run 2 with same seed
    world2 = World(spec)
    with world2:
        explorer2 = RuleBasedExplorer(
            world=world2,
            budget_steps=6,
            seed=123,
            output_dir=tmp_path / "run_2",
        )
        res2 = await explorer2.explore()

    assert res1.steps_executed == res2.steps_executed

    # Acceptance: The same seed gives the same walk
    actions1 = [a.id for a in explorer1.action_history]
    actions2 = [a.id for a in explorer2.action_history]
    assert actions1 == actions2


@pytest.mark.asyncio
async def test_trap_pages_avoid_infinite_loop(tmp_path: Path) -> None:
    spec = WorldSpec(app_id="shop_twin", bugs=[])
    world = World(spec)

    with world:
        explorer = RuleBasedExplorer(
            world=world,
            budget_steps=10,
            seed=42,
            output_dir=tmp_path / "run_trap",
        )
        res = await explorer.explore()

        # Acceptance: Explorer never gets stuck in loops and finishes within step budget
        assert res.steps_executed <= explorer.budget_steps
        assert res.duration_seconds < explorer.budget_time_seconds

