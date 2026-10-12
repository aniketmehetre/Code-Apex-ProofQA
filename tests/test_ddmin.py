"""Property-based and synthetic predicate tests for pure three-valued ddmin."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from proofqa.proof.ddmin import ddmin


def test_ddmin_monotone_predicate() -> None:
    """Predicate: fails if item 7 is present."""
    items = list(range(20))

    def predicate(sub: list[int]) -> str:
        return "FAIL" if 7 in sub else "PASS"

    min_items, log = ddmin(items, predicate)

    assert min_items == [7]
    assert any(entry["outcome"] == "FAIL" for entry in log)


def test_ddmin_pair_dependency() -> None:
    """Predicate: fails if both items 3 and 11 are present together."""
    items = list(range(16))

    def predicate(sub: list[int]) -> str:
        return "FAIL" if (3 in sub and 11 in sub) else "PASS"

    min_items, log = ddmin(items, predicate)

    assert set(min_items) == {3, 11}
    assert len(min_items) == 2


def test_ddmin_unresolved_never_reduces() -> None:
    """Predicate: item 2 is a prerequisite.

    If 2 is missing, result is UNRESOLVED (not PASS, not FAIL).
    Target bug requires item 5.
    """
    items = list(range(10))

    def predicate(sub: list[int]) -> str:
        if 2 not in sub:
            return "UNRESOLVED"
        if 5 in sub:
            return "FAIL"
        return "PASS"

    min_items, log = ddmin(items, predicate)

    # Must retain prerequisite 2 and trigger 5!
    assert set(min_items) == {2, 5}
    # Check that attempts returning UNRESOLVED were never adopted
    for entry in log:
        if entry["outcome"] == "UNRESOLVED":
            # An unresolved outcome must not be the final accepted subset
            assert entry["indices"] != [2, 5]


def test_ddmin_all_unresolved_returns_original() -> None:
    """Predicate: any reduction yields UNRESOLVED."""
    items = [1, 2, 3, 4]

    def predicate(sub: list[int]) -> str:
        if len(sub) == len(items):
            return "FAIL"
        return "UNRESOLVED"

    min_items, _ = ddmin(items, predicate)
    assert min_items == items


def test_ddmin_non_monotone_predicate() -> None:
    """Non-monotone predicate: fails if subset size is odd and contains 4."""
    items = [0, 1, 2, 3, 4, 5, 6]

    def predicate(sub: list[int]) -> str:
        if 4 in sub and len(sub) % 2 == 1:
            return "FAIL"
        return "PASS"

    min_items, _ = ddmin(items, predicate)
    assert predicate(min_items) == "FAIL"


@given(
    target=st.integers(min_value=0, max_value=29),
    extra_size=st.integers(min_value=1, max_value=20),
)
def test_hypothesis_single_target_minimality(target: int, extra_size: int) -> None:
    """Hypothesis test: a list containing target always reduces to [target]."""
    items = list(range(target + extra_size + 1))
    if target not in items:
        items.append(target)

    def predicate(sub: list[int]) -> str:
        return "FAIL" if target in sub else "PASS"

    min_items, _ = ddmin(items, predicate, budget=100)
    assert min_items == [target]


@given(
    pair=st.tuples(
        st.integers(min_value=0, max_value=14),
        st.integers(min_value=15, max_value=29),
    )
)
def test_hypothesis_pair_targets_minimality(pair: tuple[int, int]) -> None:
    """Hypothesis test: a list containing pair always reduces to the pair."""
    p1, p2 = pair
    items = list(range(35))

    def predicate(sub: list[int]) -> str:
        return "FAIL" if (p1 in sub and p2 in sub) else "PASS"

    min_items, _ = ddmin(items, predicate, budget=150)
    assert set(min_items) == {p1, p2}
    assert len(min_items) == 2
