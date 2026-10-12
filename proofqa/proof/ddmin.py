"""Pure three-valued Delta Debugging (ddmin) algorithm following Andreas Zeller's formulation.

Operates over generic items with three-valued outcome: FAIL, PASS, UNRESOLVED.
UNRESOLVED is never accepted as a reduction and never treated as PASS.
Deterministic, memoised, and bounded by a test call budget.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


def ddmin(
    items: list[T],
    test: Callable[[list[T]], str],
    budget: int = 200,
) -> tuple[list[T], list[dict[str, Any]]]:
    """Reduce items while preserving the FAIL outcome.

    Args:
        items: Initial list of items causing FAIL.
        test: Pure function taking a sublist of items and returning
              "FAIL", "PASS", or "UNRESOLVED".
        budget: Maximum number of test evaluations before stopping.

    Returns:
        (minimal_items, attempt_log)
    """
    if not items:
        return [], []

    attempt_log: list[dict[str, Any]] = []
    memo: dict[tuple[int, ...], str] = {}
    calls = 0

    # Map each original item to an index for stable tuple hashing
    indexed_items = list(enumerate(items))

    def evaluate(subset: list[tuple[int, T]]) -> str:
        nonlocal calls
        key = tuple(idx for idx, _ in subset)
        if key in memo:
            return memo[key]

        if calls >= budget:
            return "UNRESOLVED"

        calls += 1
        raw_items = [val for _, val in subset]
        outcome = test(raw_items)
        if outcome not in ("FAIL", "PASS", "UNRESOLVED"):
            outcome = "UNRESOLVED"

        memo[key] = outcome
        attempt_log.append({
            "indices": list(key),
            "size": len(key),
            "outcome": outcome,
        })
        return outcome

    # Verify initial full set reproduces FAIL
    initial_outcome = evaluate(indexed_items)
    if initial_outcome != "FAIL":
        return items, attempt_log

    current = list(indexed_items)
    n = 2

    while len(current) >= 2 and calls < budget:
        # 1. Partition current into n slices
        length = len(current)
        slices: list[list[tuple[int, T]]] = []
        chunk_size = length // n
        remainder = length % n

        start = 0
        for i in range(n):
            end = start + chunk_size + (1 if i < remainder else 0)
            slices.append(current[start:end])
            start = end

        # 2. Test each slice
        reduced = False
        for s in slices:
            if not s:
                continue
            res = evaluate(s)
            if res == "FAIL":
                current = s
                n = 2
                reduced = True
                break

        if reduced:
            continue

        # 3. Test complements (current without slice)
        for s in slices:
            complement = [item for item in current if item not in s]
            if not complement:
                continue
            res = evaluate(complement)
            if res == "FAIL":
                current = complement
                n = max(n - 1, 2)
                reduced = True
                break

        if reduced:
            continue

        # 4. Increase granularity if possible
        if n < len(current):
            n = min(len(current), 2 * n)
        else:
            # 1-minimal reached!
            break

    minimal_items = [val for _, val in current]
    return minimal_items, attempt_log


async def async_ddmin(
    items: list[T],
    test: Callable[[list[T]], Any],
    budget: int = 200,
) -> tuple[list[T], list[dict[str, Any]]]:
    """Asynchronous variant of ddmin for async predicates (e.g. browser replays).

    Identical algorithm to ddmin, but awaits the test evaluation function.
    """
    if not items:
        return [], []

    attempt_log: list[dict[str, Any]] = []
    memo: dict[tuple[int, ...], str] = {}
    calls = 0

    indexed_items = list(enumerate(items))

    async def evaluate(subset: list[tuple[int, T]]) -> str:
        nonlocal calls
        key = tuple(idx for idx, _ in subset)
        if key in memo:
            return memo[key]

        if calls >= budget:
            return "UNRESOLVED"

        calls += 1
        raw_items = [val for _, val in subset]
        outcome = await test(raw_items)
        if outcome not in ("FAIL", "PASS", "UNRESOLVED"):
            outcome = "UNRESOLVED"

        memo[key] = outcome
        attempt_log.append({
            "indices": list(key),
            "size": len(key),
            "outcome": outcome,
        })
        return outcome

    initial_outcome = await evaluate(indexed_items)
    if initial_outcome != "FAIL":
        return items, attempt_log

    current = list(indexed_items)
    n = 2

    while len(current) >= 2 and calls < budget:
        length = len(current)
        slices: list[list[tuple[int, T]]] = []
        chunk_size = length // n
        remainder = length % n

        start = 0
        for i in range(n):
            end = start + chunk_size + (1 if i < remainder else 0)
            slices.append(current[start:end])
            start = end

        reduced = False
        for s in slices:
            if not s:
                continue
            res = await evaluate(s)
            if res == "FAIL":
                current = s
                n = 2
                reduced = True
                break

        if reduced:
            continue

        for s in slices:
            complement = [item for item in current if item not in s]
            if not complement:
                continue
            res = await evaluate(complement)
            if res == "FAIL":
                current = complement
                n = max(n - 1, 2)
                reduced = True
                break

        if reduced:
            continue

        if n < len(current):
            n = min(len(current), 2 * n)
        else:
            break

    minimal_items = [val for _, val in current]
    return minimal_items, attempt_log
