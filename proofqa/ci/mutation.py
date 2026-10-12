"""Mutation score checker evaluating regression suites against planted bugs."""

from __future__ import annotations

from typing import Any

from proofbench.adjudicate import Adjudicator
from proofqa.contracts import Finding


def compute_mutation_score(findings: list[Finding]) -> dict[str, Any]:
    """Evaluates mutation kill score of finding suite against the 10 planted bugs."""
    adjudicator = Adjudicator()
    killed_mutants: set[str] = set()

    credited: set[str] = set()
    for f in findings:
        status, bid = adjudicator.adjudicate(f, credited)
        if status == "true_bug" and bid:
            killed_mutants.add(bid)
            credited.add(bid)

    total_mutants = 10
    score = len(killed_mutants) / total_mutants

    return {
        "killed_mutants_count": len(killed_mutants),
        "total_mutants": total_mutants,
        "mutation_score": round(score, 4),
        "killed_mutants": sorted(list(killed_mutants)),
    }
