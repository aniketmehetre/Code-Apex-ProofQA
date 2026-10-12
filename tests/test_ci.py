"""Acceptance tests for Phase 12 CI Delivery (Prompt 12.1)."""

from __future__ import annotations

from pathlib import Path

from proofqa.ci.comment import generate_pr_comment
from proofqa.ci.mutation import compute_mutation_score
from proofqa.contracts import (
    Action,
    ActionKind,
    FailureSignature,
    Finding,
    OracleClass,
    Tier,
)


def test_github_action_file_exists() -> None:
    action_file = Path(".github/workflows/proofqa.yml")
    assert action_file.exists()
    content = action_file.read_text(encoding="utf-8")
    assert "proofqa run" in content
    assert "proofqa verify" in content


def test_pr_comment_generation(tmp_path: Path) -> None:
    # 1. Clean run comment
    clean_comment = generate_pr_comment(tmp_path / "non_existent")
    assert "Zero behavioral regressions" in clean_comment

    # 2. Populated certificates run
    cert_dir = tmp_path / "cert_01"
    cert_dir.mkdir(parents=True)
    (cert_dir / "manifest.json").write_text('{"created_at": "2026-10-13"}', encoding="utf-8")
    (cert_dir / "claim.json").write_text(
        '{"claim": "Zero quantity cart returns 500", "oracle_class": "A", "tier": "VERIFIED"}',
        encoding="utf-8",
    )

    pr_comment = generate_pr_comment(tmp_path)
    assert "ProofQA Verification Report: 1 Issue(s) Certified" in pr_comment
    assert "cert_01" in pr_comment
    assert "Zero quantity cart returns 500" in pr_comment


def test_mutation_score_computation() -> None:
    sig = FailureSignature(
        kind="http_5xx",
        first_party_endpoint="/api/cart",
        status=500,
        message_norm="ZeroQuantityException",
    )
    f_b01 = Finding(
        id="f_mutant_1",
        oracle_class=OracleClass.A,
        tier=Tier.VERIFIED,
        signature=sig,
        claim="Zero quantity cart returns 500",
        steps=[Action(id="a0", kind=ActionKind.GOTO, value="/")],
    )

    res = compute_mutation_score([f_b01])
    assert res["killed_mutants_count"] == 1
    assert "B01" in res["killed_mutants"]
    assert res["mutation_score"] == 0.1
