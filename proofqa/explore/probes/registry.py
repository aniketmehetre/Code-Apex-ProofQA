"""Probe registry managing probe execution order, budgets, and state memoization."""

from __future__ import annotations

from dataclasses import dataclass, field

from proofqa.contracts import Action
from proofqa.explore.grounding import ground_action
from proofqa.explore.probes.base import Probe, ProbeContext


@dataclass
class ProbeRegistry:
    """Deterministic probe registry with per-probe budgets and per-state memoization."""

    probes: list[Probe] = field(default_factory=list)
    per_probe_budget: int = 10
    _run_counts: dict[str, int] = field(default_factory=dict)
    _tried_memo: set[tuple[str, str]] = field(default_factory=set)

    def register(self, probe: Probe) -> None:
        """Registers a probe, avoiding duplicates."""
        if any(p.name == probe.name for p in self.probes):
            return
        self.probes.append(probe)
        # Ensure probes are sorted deterministically by name
        self.probes.sort(key=lambda p: p.name)

    def is_memoized(self, probe_name: str, semantic_state_key: str) -> bool:
        """Returns True if the probe was already executed on this semantic state."""
        return (probe_name, semantic_state_key) in self._tried_memo

    def get_remaining_budget(self, probe_name: str) -> int:
        """Returns remaining execution budget for given probe."""
        return max(0, self.per_probe_budget - self._run_counts.get(probe_name, 0))

    def run_applicable_probes(
        self,
        ctx: ProbeContext,
        max_probes_per_page: int = 5,
    ) -> list[Action]:
        """Runs applicable probes deterministically up to the per-page cap and budget.

        Actions produced are passed through ground_action against ctx.grounded_controls.
        """
        planned_actions: list[Action] = []
        probes_fired = 0

        # Run in deterministic order
        for probe in sorted(self.probes, key=lambda p: p.name):
            if probes_fired >= max_probes_per_page:
                break
            if ctx.budget_left <= 0:
                break

            probe_name = probe.name
            if self.is_memoized(probe_name, ctx.semantic_state_key):
                continue

            if self.get_remaining_budget(probe_name) <= 0:
                continue

            # Check if probe applies to this context
            if not probe.applies(ctx):
                continue

            # Record memo and increment run count
            self._tried_memo.add((probe_name, ctx.semantic_state_key))
            self._run_counts[probe_name] = self._run_counts.get(probe_name, 0) + 1
            probes_fired += 1

            # Plan probe actions
            proposed = probe.plan(ctx)

            # Ground all proposed actions through grounding choke point
            for act in proposed:
                grounded = ground_action(act, ctx.grounded_controls)
                if grounded is not None:
                    planned_actions.append(grounded)

        return planned_actions
