"""BurstProbe: Concurrent burst dispatch for intermittent / concurrency defects (Prompt 8).

Dispatches N concurrent repeats of mutating actions (e.g. Add to Cart) to expose
concurrency lock timeouts, transient race conditions, and rate limits.
"""

from __future__ import annotations

from proofqa.contracts import Action, ActionKind
from proofqa.explore.probes.base import Probe, ProbeContext


class BurstProbe(Probe):
    """Executes rapid concurrent burst clicks against mutating actions."""

    def __init__(self, burst_size: int = 5) -> None:
        self.burst_size = burst_size

    @property
    def name(self) -> str:
        return "burst"

    def applies(self, ctx: ProbeContext) -> bool:
        """Applies when mutating interactive controls (add to cart, checkout, apply) are present."""
        for c in ctx.grounded_controls:
            if c.kind != ActionKind.CLICK or not c.locator:
                continue
            text = " ".join(filter(None, [c.locator.name, c.locator.label, c.locator.testid])).lower()
            if any(k in text for k in ["add to cart", "add item", "buy", "modal-add-to-cart", "confirm"]):
                return True
        return False

    def plan(self, ctx: ProbeContext) -> list[Action]:
        """Plans a burst action repeating the target click concurrently N times."""
        for c in ctx.grounded_controls:
            if c.kind != ActionKind.CLICK or not c.locator:
                continue
            text = " ".join(filter(None, [c.locator.name, c.locator.label, c.locator.testid])).lower()
            if any(k in text for k in ["add to cart", "add item", "buy", "modal-add-to-cart", "confirm"]):
                return [
                    Action(
                        id=f"burst_{c.id}",
                        kind=c.kind,
                        locator=c.locator,
                        value=c.value,
                        params=c.params,
                        burst=self.burst_size,
                    )
                ]
        return []
