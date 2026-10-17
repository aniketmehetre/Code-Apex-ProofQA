"""BoundaryProbe: systematic boundary value exploration on form inputs (Prompt 4)."""

from __future__ import annotations

from proofqa.contracts import Action, ActionKind
from proofqa.explore.forms import extract_form_plans
from proofqa.explore.probes.base import Probe, ProbeContext


class BoundaryProbe(Probe):
    """Systematically evaluates boundary values and edge inputs on grounded form controls."""

    def __init__(self) -> None:
        self._unresolved_count: int = 0

    @property
    def name(self) -> str:
        return "boundary"

    @property
    def unresolved_count(self) -> int:
        return self._unresolved_count

    def applies(self, ctx: ProbeContext) -> bool:
        """Applies if grounded controls contain at least one input field."""
        has_input = any(c.kind in (ActionKind.FILL, ActionKind.SELECT) for c in ctx.grounded_controls)
        return has_input

    def plan(self, ctx: ProbeContext) -> list[Action]:
        """Plans a sequence filling baseline valid values and altering one field to a boundary value."""
        plans = extract_form_plans(ctx.grounded_controls)
        if not plans:
            return []

        form_plan = plans[0]
        baseline = form_plan.baseline_values(fact_store=ctx.spec_facts)
        actions: list[Action] = []

        # Iterate over fields and pick boundary variations
        for target_field in form_plan.fields:
            variants = form_plan.boundary_variants_for_field(target_field, fact_store=ctx.spec_facts)
            if not variants:
                continue

            # Deterministically select variants
            chosen_variant = variants[0]

            # 1. Fill non-target fields with valid baseline values
            for f in form_plan.fields:
                if f.id != target_field.id:
                    val = baseline.get(f.id, "Valid Entry")
                    actions.append(
                        Action(
                            id=f"boundary_base_{f.id}",
                            kind=ActionKind.FILL,
                            locator=f.locator,
                            value=val,
                            params=f.params,
                        )
                    )

            # 2. Fill target field with boundary variant
            actions.append(
                Action(
                    id=f"boundary_val_{target_field.id}",
                    kind=ActionKind.FILL,
                    locator=target_field.locator,
                    value=chosen_variant,
                    params=target_field.params,
                )
            )

            # 3. Submit the form
            if form_plan.submit_control:
                actions.append(
                    Action(
                        id=f"boundary_submit_{form_plan.submit_control.id}",
                        kind=ActionKind.CLICK,
                        locator=form_plan.submit_control.locator,
                        params=form_plan.submit_control.params,
                    )
                )

            # One boundary sequence per plan invocation
            break

        return actions
