"""InversePairProbe: Systematic execution of inverse operation pairs (Prompt 5).

Exercises forward/backward metamorphic pairs:
- Add then remove
- Apply code then clear code
- Check then uncheck
"""

from __future__ import annotations

from proofqa.contracts import Action
from proofqa.explore.probes.base import Probe, ProbeContext


class InversePairProbe(Probe):
    """Executes reciprocal action pairs to test cancellation and cleanup invariants."""

    @property
    def name(self) -> str:
        return "inverse_pair"

    def applies(self, ctx: ProbeContext) -> bool:
        """Applies if grounded controls contain add/remove, apply/clear, or toggle actions."""
        for c in ctx.grounded_controls:
            loc = c.locator
            if not loc:
                continue
            name = (loc.name or "").lower()
            testid = (loc.testid or "").lower()
            if any(k in name or k in testid for k in ["add to cart", "add item", "apply", "remove", "delete"]):
                return True
        return False

    def plan(self, ctx: ProbeContext) -> list[Action]:
        """Plans paired forward and inverse actions."""
        forward_actions: list[Action] = []
        inverse_actions: list[Action] = []

        for c in ctx.grounded_controls:
            loc = c.locator
            if not loc:
                continue
            text = " ".join(filter(None, [loc.name, loc.label, loc.testid])).lower()
            if any(k in text for k in ["add to cart", "add item", "buy", "modal-add-to-cart"]):
                forward_actions.append(c)
            elif any(k in text for k in ["remove", "delete", "trash", "clear", "cancel"]):
                inverse_actions.append(c)

        actions: list[Action] = []
        if forward_actions and inverse_actions:
            # Both forward and inverse are already visible
            actions.append(forward_actions[0])
            actions.append(inverse_actions[0])
        elif forward_actions:
            # Execute forward action; subsequent state extraction will expose the inverse
            actions.append(forward_actions[0])
        elif inverse_actions:
            # Execute inverse cleanup
            actions.append(inverse_actions[0])

        return actions
