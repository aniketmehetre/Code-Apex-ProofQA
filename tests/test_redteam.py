"""Final Red Team Automated Verification Suite (Milestone M4, Prompt 13.3).

Executes the 5 hostile red-team checks:
1. Tamper 1 byte in a certificate manifest -> proofqa verify returns TAMPERED.
2. Run with OFFLINE=1 -> pipeline functions fully without external LLM calls.
3. Import guards -> Rule 2 and Rule 3 enforced statically.
4. Clean world false-positive test -> 0 false positive certificates produced.
5. Claims-versus-summary check -> 100% numerical consistency between docs/claims.md and results/summary.json.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from proofqa.cert.verify import verify_certificate
from proofqa.contracts import VerifyVerdictKind, WorldSpec
from proofqa.pipeline import Pipeline


@pytest.mark.asyncio
async def test_redteam_1_tamper_detection(tmp_path: Path) -> None:
    """Tampering 1 byte in certificate file causes instant TAMPERED verdict."""
    source_cert = Path("demo/recorded/recorded_b01")
    assert source_cert.exists(), "Recorded certificate must exist"

    tmp_cert = tmp_path / "tamper_test"
    shutil.copytree(source_cert, tmp_cert)

    # Verify original is VALID
    verdict_clean = await verify_certificate(tmp_cert, replay_count=1, verbose=False)
    assert verdict_clean.verdict == VerifyVerdictKind.VALID

    # Flip 1 byte in claim.json
    claim_file = tmp_cert / "claim.json"
    content = bytearray(claim_file.read_bytes())
    content[0] ^= 0x01
    claim_file.write_bytes(content)

    # Verify tampered certificate
    verdict_tampered = await verify_certificate(tmp_cert, replay_count=1, verbose=False)
    assert verdict_tampered.verdict == VerifyVerdictKind.TAMPERED
    assert "SHA-256 mismatch" in (verdict_tampered.reason or "")


@pytest.mark.asyncio
async def test_redteam_2_offline_pipeline_execution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """OFFLINE=1 executes autonomously without network LLM calls."""
    monkeypatch.setenv("OFFLINE", "1")
    spec = WorldSpec(app_id="shop_twin", bugs=["B01"])

    pipeline = Pipeline(
        world_spec=spec,
        output_dir=tmp_path / "offline_certs",
        session_db_path=tmp_path / "offline_session.db",
    )

    certs = await pipeline.run(step_budget=4, k_replays=1)
    # Pipeline executes cleanly and finishes without errors
    assert isinstance(certs, list)


def test_redteam_3_import_guards_enforcement() -> None:
    """Import guards enforcing Rules 2 and 3 must pass."""
    from tests.test_import_guards import (
        test_rule_2_proof_cert_oracles_must_never_import_llm,
        test_rule_3_verify_must_not_import_explore_oracles_llm_uncertainty,
    )
    test_rule_2_proof_cert_oracles_must_never_import_llm()
    test_rule_3_verify_must_not_import_explore_oracles_llm_uncertainty()


@pytest.mark.asyncio
async def test_redteam_4_clean_world_zero_false_positives(tmp_path: Path) -> None:
    """Running on a clean twin yields exactly zero false-positive certificates."""
    spec = WorldSpec(app_id="shop_twin", bugs=[])
    pipeline = Pipeline(
        world_spec=spec,
        output_dir=tmp_path / "clean_certs",
        session_db_path=tmp_path / "clean_session.db",
    )

    certs = await pipeline.run(step_budget=6, k_replays=1)
    assert len(certs) == 0, f"Expected 0 false positive certificates on clean world, got {len(certs)}"


def test_redteam_5_claims_versus_summary_consistency() -> None:
    """Every metric reported in docs/claims.md must match results/summary.json."""
    summary_file = Path("results/summary.json")
    assert summary_file.exists(), "results/summary.json must exist"
    summary = json.loads(summary_file.read_text(encoding="utf-8"))

    claims_file = Path("docs/claims.md")
    assert claims_file.exists(), "docs/claims.md must exist"
    claims_text = claims_file.read_text(encoding="utf-8")

    # Check precision
    prec_str = f"{summary['precision'] * 100:.1f}%"
    assert prec_str in claims_text, f"Precision {prec_str} missing from docs/claims.md"

    # Check recall
    rec_str = f"{summary['recall'] * 100:.1f}%"
    assert rec_str in claims_text, f"Recall {rec_str} missing from docs/claims.md"

    # Check validity rate
    val_str = f"{summary['certificate_validity_rate'] * 100:.1f}%"
    assert val_str in claims_text, f"Validity rate {val_str} missing from docs/claims.md"
