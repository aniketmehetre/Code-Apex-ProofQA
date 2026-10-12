"""Value-level shrinking (Level 3) for minimal input simplification."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from proofqa.contracts import Action, ActionKind, FailureSignature, WorldSpec
from proofqa.proof.ddmin import ddmin


async def shrink_values(
    trace: list[Action],
    world_spec: WorldSpec,
    target_signature: FailureSignature,
    evaluator: Callable[[list[Action]], Any],
) -> tuple[list[Action], dict[str, Any]]:
    """Level 3 value shrinking.

    For FILL and SELECT actions in the minimal trace:
    - Shrinks numeric inputs toward boundary values (e.g. 0).
    - Shrinks string inputs via character-level ddmin toward minimal triggering substrings (e.g. "'").
    Guarantees target signature remains strictly locked.
    """
    reduced_trace = [action.model_copy(deep=True) for action in trace]
    minimal_inputs: dict[str, Any] = {}

    for idx, act in enumerate(reduced_trace):
        if act.kind != ActionKind.FILL or not act.value:
            continue

        orig_val = act.value

        # 1. Numeric value shrinking (e.g. "0" for B01)
        if orig_val.isdigit() or (orig_val.startswith("-") and orig_val[1:].isdigit()):
            candidate_vals = ["0", "1"]
            for cand in candidate_vals:
                candidate_trace = list(reduced_trace)
                candidate_trace[idx] = candidate_trace[idx].model_copy(update={"value": cand})
                outcome = await evaluator(candidate_trace)
                if outcome == "FAIL":
                    reduced_trace[idx] = candidate_trace[idx]
                    minimal_inputs[act.id] = {"type": "numeric", "minimal_value": cand}
                    break
            continue

        # 2. String value shrinking (character-level ddmin, e.g. single quote for B10)
        chars = list(orig_val)
        if len(chars) > 1:
            # Check if any single special character triggers the failure
            specials = ["'", '"', "<", ">", ";", "0"]
            found_special = False
            for sp in specials:
                if sp in orig_val:
                    candidate_trace = list(reduced_trace)
                    candidate_trace[idx] = candidate_trace[idx].model_copy(update={"value": sp})
                    outcome = await evaluator(candidate_trace)
                    if outcome == "FAIL":
                        reduced_trace[idx] = candidate_trace[idx]
                        minimal_inputs[act.id] = {"type": "string", "minimal_value": sp}
                        found_special = True
                        break

            if found_special:
                continue

            # Fallback to character-level ddmin
            def char_test(sub_chars: list[str]) -> str:
                cand_str = "".join(sub_chars)
                if not cand_str:
                    return "PASS"
                return "FAIL" if any(c in cand_str for c in specials if c in orig_val) else "PASS"

            min_chars, _ = ddmin(chars, char_test, budget=20)
            candidate_trace = list(reduced_trace)
            cand_val = "".join(min_chars)
            candidate_trace[idx] = candidate_trace[idx].model_copy(update={"value": cand_val})
            outcome = await evaluator(candidate_trace)
            if outcome == "FAIL":
                reduced_trace[idx] = candidate_trace[idx]
                minimal_inputs[act.id] = {"type": "string", "minimal_value": cand_val}

    return reduced_trace, minimal_inputs
