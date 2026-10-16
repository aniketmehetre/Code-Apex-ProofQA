"""Unit tests for Probe protocol and ProbeRegistry."""

from __future__ import annotations

import random

from proofqa.contracts import Action, ActionKind, Locator
from proofqa.explore.probes.base import Probe, ProbeContext
from proofqa.explore.probes.registry import ProbeRegistry


class DummyProbe(Probe):
    def __init__(self, name: str, return_actions: list[Action] | None = None) -> None:
        self._name = name
        self._actions = return_actions or []

    @property
    def name(self) -> str:
        return self._name

    def applies(self, ctx: ProbeContext) -> bool:
        return True

    def plan(self, ctx: ProbeContext) -> list[Action]:
        return list(self._actions)


def test_probe_registry_deterministic_order_and_memo():
    ctrl1 = Action(id="c1", kind=ActionKind.CLICK, locator=Locator(role="button", name="Submit"))
    ctrl2 = Action(id="c2", kind=ActionKind.FILL, locator=Locator(role="textbox", name="Email"))
    grounded = [ctrl1, ctrl2]

    p_b = DummyProbe("probe_b", [ctrl1])
    p_a = DummyProbe("probe_a", [ctrl2])

    registry = ProbeRegistry(per_probe_budget=2)
    # Register out of order
    registry.register(p_b)
    registry.register(p_a)

    # Must be sorted deterministically by name
    assert [p.name for p in registry.probes] == ["probe_a", "probe_b"]

    ctx = ProbeContext(
        grounded_controls=grounded,
        semantic_state_key="page_home:hash1",
        budget_left=10,
        rng=random.Random(42),
    )

    # First run on state key: both probes run
    actions = registry.run_applicable_probes(ctx)
    assert len(actions) == 2
    assert actions[0].locator.name == "Email"  # probe_a
    assert actions[1].locator.name == "Submit"  # probe_b

    # Second run on same state key: both memoized!
    actions2 = registry.run_applicable_probes(ctx)
    assert len(actions2) == 0

    # Run on a different state key: budget remaining is 1 for each
    ctx2 = ProbeContext(
        grounded_controls=grounded,
        semantic_state_key="page_home:hash2",
        budget_left=10,
        rng=random.Random(42),
    )
    actions3 = registry.run_applicable_probes(ctx2)
    assert len(actions3) == 2

    # Third run on a third state key: per-probe budget of 2 is now exhausted!
    ctx3 = ProbeContext(
        grounded_controls=grounded,
        semantic_state_key="page_home:hash3",
        budget_left=10,
        rng=random.Random(42),
    )
    actions4 = registry.run_applicable_probes(ctx3)
    assert len(actions4) == 0
    assert registry.get_remaining_budget("probe_a") == 0
    assert registry.get_remaining_budget("probe_b") == 0


def test_probe_registry_drops_ungrounded_actions():
    ctrl = Action(id="c1", kind=ActionKind.CLICK, locator=Locator(role="button", name="Real Button"))
    # Probe proposes ungrounded click
    fake_act = Action(id="fake", kind=ActionKind.CLICK, locator=Locator(role="button", name="Fake Injected Button"))

    p = DummyProbe("p_ungrounded", [fake_act, ctrl])
    registry = ProbeRegistry()
    registry.register(p)

    ctx = ProbeContext(
        grounded_controls=[ctrl],
        semantic_state_key="state1",
        budget_left=5,
    )
    actions = registry.run_applicable_probes(ctx)
    # Only grounded action should survive
    assert len(actions) == 1
    assert actions[0].locator.name == "Real Button"
