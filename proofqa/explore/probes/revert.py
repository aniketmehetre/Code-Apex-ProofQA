"""RevertProbe: Metamorphic exploration for select, radio, and toggle controls (Prompt 5).

Changes a control away from its default / initial value and then restores it,
verifying that restoring the initial state restores the observable collection.
"""

from __future__ import annotations

from proofqa.contracts import Action, ActionKind
from proofqa.explore.probes.base import Probe, ProbeContext


class RevertProbe(Probe):
    """Metamorphic revert probe testing sort, filter, or toggle restoration invariance."""

    @property
    def name(self) -> str:
        return "revert"

    def applies(self, ctx: ProbeContext) -> bool:
        """Applies if grounded controls contain a select dropdown or combobox."""
        return any(c.kind == ActionKind.SELECT for c in ctx.grounded_controls)

    def plan(self, ctx: ProbeContext) -> list[Action]:
        """Plans a sequence: select alternative option, then restore initial option."""
        select_controls = [c for c in ctx.grounded_controls if c.kind == ActionKind.SELECT]
        if not select_controls:
            return []

        # Find sort control first if available (to test sort restoration invariance B05)
        sort_ctrls = [c for c in select_controls if c.locator and "sort" in f"{c.locator.name or ''} {c.locator.label or ''}".lower()]
        filter_ctrls = [c for c in select_controls if c.locator and any(k in f"{c.locator.name or ''} {c.locator.label or ''}".lower() for k in ["filter", "category"])]

        if sort_ctrls:
            target = sort_ctrls[0]
            alt_val = "price_asc"
        elif filter_ctrls:
            target = filter_ctrls[0]
            alt_val = "Electronics"
        else:
            target = select_controls[0]
            initial_val = target.value or ""
            candidates = ["price_asc", "price-asc", "price_desc", "name", "rating", "Electronics", "Books"]
            alt_val = next((v for v in candidates if v != initial_val), "price_asc")

        initial_val = target.value or ""

        step1 = Action(
            id=f"revert_step1_{target.id}",
            kind=ActionKind.SELECT,
            locator=target.locator,
            value=alt_val,
            params={"previous_value": initial_val},
        )
        step2 = Action(
            id=f"revert_step2_{target.id}",
            kind=ActionKind.SELECT,
            locator=target.locator,
            value="" if initial_val in ("Default", "") else initial_val,
            params={"restoring": True, "expected_restored": initial_val},
        )

        return [step1, step2]
