"""Form model and FormPlan abstraction for systematic form interaction (Prompt 4)."""

from __future__ import annotations

import random
from dataclasses import dataclass

from proofqa.contracts import Action, ActionKind
from proofqa.spec.facts import SpecFactStore

# Standard generic boundary values across all input types
GENERIC_BOUNDARY_STRINGS = [
    "0",
    "-1",
    "",
    "a" * 5000,
    "'",
    '"',
    "%",
    "\\",
    "⚡🚀Ω≈ç√∫˜µ",
]


@dataclass
class FormPlan:
    """Represents a coherent group of form inputs and their corresponding submit action."""

    fields: list[Action]
    submit_control: Action | None = None

    def get_field_subject(self, input_field: Action) -> str:
        """Determines the semantic subject for an input field based on its locator."""
        loc = input_field.locator
        if not loc:
            return "field"
        text = " ".join(filter(None, [loc.name, loc.label, loc.testid, loc.role])).lower()
        for kw in ["password", "quantity", "email", "address", "phone", "username", "coupon", "promo", "search"]:
            if kw in text:
                return kw
        return "text"

    def baseline_values(
        self,
        seed: int = 42,
        fact_store: SpecFactStore | None = None,
    ) -> dict[str, str]:
        """Generates deterministic, valid baseline values satisfying known specification facts."""
        values: dict[str, str] = {}
        rng = random.Random(seed)

        for f in self.fields:
            subj = self.get_field_subject(f)
            if subj == "password":
                min_len = 8
                if fact_store:
                    fact_min = fact_store.get_fact_value("password", "min_len")
                    if fact_min is not None:
                        min_len = int(fact_min)
                target_len = max(min_len, 12)
                values[f.id] = f"P@ssw0rd{seed}!{'x' * max(0, target_len - 11)}"

            elif subj == "email":
                values[f.id] = f"user_{seed}_{rng.randint(100, 999)}@example.com"

            elif subj == "quantity":
                min_val = 1
                if fact_store:
                    fact_min = fact_store.get_fact_value("quantity", "min")
                    if fact_min is not None:
                        min_val = int(fact_min)
                values[f.id] = str(max(1, min_val))

            elif subj in ("coupon", "promo"):
                values[f.id] = "SAVE20"

            elif subj == "phone":
                values[f.id] = "5550199"

            elif subj == "address":
                values[f.id] = "742 Evergreen Terrace, Springfield"

            else:
                values[f.id] = "Valid Test Entry"

        return values

    def boundary_variants_for_field(
        self,
        target_field: Action,
        fact_store: SpecFactStore | None = None,
    ) -> list[str]:
        """Returns ordered list of boundary and edge-case values for a single field."""
        subj = self.get_field_subject(target_field)
        variants: list[str] = []

        if subj == "quantity":
            min_val = 1
            max_val = 99
            if fact_store:
                f_min = fact_store.get_fact_value("quantity", "min")
                f_max = fact_store.get_fact_value("quantity", "max")
                if f_min is not None:
                    min_val = int(f_min)
                if f_max is not None:
                    max_val = int(f_max)
            num_variants = [
                str(min_val - 1),
                str(min_val),
                str(min_val + 1),
                str(max_val),
                str(max_val + 1),
                "0",
                "-1",
            ]
            for nv in num_variants:
                if nv not in variants:
                    variants.append(nv)

        elif subj == "password":
            min_len = 8
            if fact_store:
                f_min = fact_store.get_fact_value("password", "min_len")
                if f_min is not None:
                    min_len = int(f_min)
            pw_variants = [
                "pass",  # Short password (violates min_len >= 8)
                "a" * max(1, min_len - 1),
                "a" * min_len,
                "a" * (min_len + 1),
            ]
            for pv in pw_variants:
                if pv not in variants:
                    variants.append(pv)

        # Append generic boundary strings
        for g in GENERIC_BOUNDARY_STRINGS:
            if g not in variants:
                variants.append(g)

        return variants


def extract_form_plans(grounded_controls: list[Action]) -> list[FormPlan]:
    """Groups grounded input controls and submit buttons into coherent FormPlans."""
    inputs: list[Action] = []
    submits: list[Action] = []

    for act in grounded_controls:
        if act.kind in (ActionKind.FILL, ActionKind.SELECT):
            inputs.append(act)
        elif act.kind == ActionKind.CLICK and act.locator:
            name = (act.locator.name or "").strip().lower()
            role = (act.locator.role or "").strip().lower()
            testid = (act.locator.testid or "").strip().lower()
            if any(term in name or term in testid for term in ["submit", "register", "login", "confirm", "add to cart", "apply"]):
                submits.append(act)
            elif role == "button" and any(term in name for term in ["save", "checkout", "search", "update"]):
                submits.append(act)

    if not inputs:
        return []

    # If we have submit buttons, pair inputs with submit button
    plans: list[FormPlan] = []
    if submits:
        for s in submits:
            plans.append(FormPlan(fields=list(inputs), submit_control=s))
    else:
        # Standalone inputs without an explicit submit button
        plans.append(FormPlan(fields=list(inputs), submit_control=None))

    return plans
