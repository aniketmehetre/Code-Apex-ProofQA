"""Multi-level browser test case shrinking preserving locked failure signature.

Levels:
- Level 1: State-drop (remove redundant steps without state or network impact).
- Level 2: Three-valued delta-debugging (ddmin) over action sequences/dependency blocks.
- Level 3: Value shrinking (numeric boundary and character-level ddmin for inputs).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from proofqa.contracts import (
    Action,
    ActionKind,
    FailureSignature,
    WorldSpec,
)
from proofqa.proof.ddmin import async_ddmin
from proofqa.proof.replay import replay
from proofqa.proof.value_shrink import shrink_values


@dataclass
class ShrinkResult:
    """Outcome of multi-level trace minimization."""

    original_trace: list[Action]
    reduced_trace: list[Action]
    target_signature: FailureSignature
    replays_used: int
    wall_time_ms: float
    attempt_log: list[dict[str, Any]]
    level1_size: int
    level2_size: int
    level3_minimal_inputs: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_size": len(self.original_trace),
            "reduced_size": len(self.reduced_trace),
            "level1_size": self.level1_size,
            "level2_size": self.level2_size,
            "replays_used": self.replays_used,
            "wall_time_ms": self.wall_time_ms,
            "minimal_inputs": self.level3_minimal_inputs,
            "reduced_trace": [a.model_dump() for a in self.reduced_trace],
        }


async def shrink(
    trace: list[Action],
    world_spec: WorldSpec,
    target_signature: FailureSignature,
    budget: int = 50,
    enable_level3: bool = True,
) -> ShrinkResult:
    """Shrink a trace to 1-minimal steps while locking target failure signature."""
    start_time = time.time()
    replays_used = 0
    attempt_log: list[dict[str, Any]] = []

    is_intermittent = any(getattr(a, "burst", 1) > 1 for a in trace)

    async def evaluate_trace(cand_trace: list[Action]) -> str:
        nonlocal replays_used
        replays_used += 1
        n_replays = 5 if is_intermittent else 1
        rep = await replay(
            trace=cand_trace,
            world_spec=world_spec,
            n=n_replays,
            target_signature=target_signature,
            concurrency=1,
            use_cache=True,
        )
        if is_intermittent:
            if rep.fail_count >= 2:
                return "FAIL"
            elif rep.unresolved_count > 0:
                return "UNRESOLVED"
            else:
                return "PASS"
        else:
            if rep.fail_count > 0:
                return "FAIL"
            elif rep.unresolved_count > 0:
                return "UNRESOLVED"
            else:
                return "PASS"

    # --- Level 1: State drop / No-op filtration ---
    # Remove pure WAIT actions or duplicate consecutive navigation if redundant
    l1_trace: list[Action] = []
    for act in trace:
        if act.kind == ActionKind.WAIT and (not act.value or act.value == "0"):
            continue
        l1_trace.append(act)

    level1_size = len(l1_trace)

    # --- Level 2: Three-Valued Delta-Debugging (ddmin) ---
    async def async_evaluator(cand_trace: list[Action]) -> str:
        # Avoid dropping root navigation or empty trace
        if not cand_trace:
            return "PASS"
        if cand_trace[0].kind != ActionKind.GOTO and any(a.kind == ActionKind.GOTO for a in trace):
            # Prerequisite root navigation missing
            return "UNRESOLVED"
        return await evaluate_trace(cand_trace)

    # Run async ddmin over the trace actions
    reduced_actions, ddmin_log = await async_ddmin(l1_trace, async_evaluator, budget=budget)
    attempt_log.extend(ddmin_log)

    # Burst size minimization for intermittent actions (Prompt 8: keep smallest burst that still triggers)
    if is_intermittent and any(getattr(a, "burst", 1) > 1 for a in reduced_actions):
        minimized_burst_actions: list[Action] = []
        for a in reduced_actions:
            current_burst = getattr(a, "burst", 1)
            if current_burst > 1:
                best_burst = current_burst
                for candidate_burst in range(2, current_burst):
                    test_trace = [
                        (act.model_copy(update={"burst": candidate_burst}) if act.id == a.id else act)
                        for act in reduced_actions
                    ]
                    status = await evaluate_trace(test_trace)
                    if status == "FAIL":
                        best_burst = candidate_burst
                        break
                minimized_burst_actions.append(a.model_copy(update={"burst": best_burst}))
            else:
                minimized_burst_actions.append(a)
        reduced_actions = minimized_burst_actions

    level2_size = len(reduced_actions)

    # --- Level 3: Value Shrinking ---
    minimal_inputs: dict[str, Any] = {}
    final_trace = reduced_actions
    if enable_level3 and reduced_actions:
        final_trace, minimal_inputs = await shrink_values(
            trace=reduced_actions,
            world_spec=world_spec,
            target_signature=target_signature,
            evaluator=evaluate_trace,
        )

    wall_time_ms = (time.time() - start_time) * 1000

    return ShrinkResult(
        original_trace=trace,
        reduced_trace=final_trace,
        target_signature=target_signature,
        replays_used=replays_used,
        wall_time_ms=wall_time_ms,
        attempt_log=attempt_log,
        level1_size=level1_size,
        level2_size=level2_size,
        level3_minimal_inputs=minimal_inputs,
    )
