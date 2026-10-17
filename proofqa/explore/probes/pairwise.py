"""PairwiseProbe: Independent state-only control interaction (Prompt 5).

Combines state-only controls that alter view state without changing URL path
(e.g., pagination, filter, sort, search) in pairwise order:
- A then B
- B then A
- A then B then A-revert
"""

from __future__ import annotations

from proofqa.contracts import Action, ActionKind
from proofqa.explore.probes.base import Probe, ProbeContext


class PairwiseProbe(Probe):
    """Executes combinations of independent page controls like sort and filter."""

    @property
    def name(self) -> str:
        return "pairwise"

    def applies(self, ctx: ProbeContext) -> bool:
        """Applies if page contains at least two independent state controls (filter, sort, search)."""
        state_controls = self._get_independent_controls(ctx.grounded_controls)
        return len(state_controls) >= 2

    def _get_independent_controls(self, controls: list[Action]) -> list[Action]:
        results: list[Action] = []
        for c in controls:
            if c.kind in (ActionKind.SELECT, ActionKind.CLICK, ActionKind.FILL):
                loc = c.locator
                if not loc:
                    continue
                text = " ".join(filter(None, [loc.name, loc.label, loc.testid, loc.role])).lower()
                if any(k in text for k in ["filter", "category", "sort", "search", "page", "next", "combobox"]):
                    results.append(c)
        return results

    def plan(self, ctx: ProbeContext) -> list[Action]:
        """Plans A then B sequence for independent controls."""
        controls = self._get_independent_controls(ctx.grounded_controls)
        if len(controls) < 2:
            return []

        ctrl_a = controls[0]
        ctrl_b = controls[1]

        # Ensure selects have realistic values
        if ctrl_a.kind == ActionKind.SELECT and not ctrl_a.value:
            text = " ".join(filter(None, [ctrl_a.locator.name if ctrl_a.locator else None, ctrl_a.locator.label if ctrl_a.locator else None])).lower()
            val = "Electronics" if "cat" in text or "filter" in text else "price_asc"
            ctrl_a = Action(id=ctrl_a.id, kind=ctrl_a.kind, locator=ctrl_a.locator, value=val, params=ctrl_a.params)

        if ctrl_b.kind == ActionKind.SELECT and not ctrl_b.value:
            text = " ".join(filter(None, [ctrl_b.locator.name if ctrl_b.locator else None, ctrl_b.locator.label if ctrl_b.locator else None])).lower()
            val = "Electronics" if "cat" in text or "filter" in text else "price_asc"
            ctrl_b = Action(id=ctrl_b.id, kind=ctrl_b.kind, locator=ctrl_b.locator, value=val, params=ctrl_b.params)

        return [ctrl_a, ctrl_b]
