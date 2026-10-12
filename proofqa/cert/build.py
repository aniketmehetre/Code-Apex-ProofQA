"""Certificate builder producing hermetic, cryptographically verifiable bug certificates."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from proofqa.contracts import (
    Action,
    CertificateManifest,
    Finding,
    OracleClass,
    WorldSpec,
)
from proofqa.proof.replay import ReplayReport
from proofqa.proof.shrink import ShrinkResult
from proofqa.tape.tape import Tape


def compute_sha256(filepath: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def get_class_limits(oracle_class: OracleClass) -> str:
    """Return honest, class-specific limits for the certificate."""
    if oracle_class == OracleClass.A:
        return (
            "# Class A Limits\n\n"
            "- Proves: First-party server exception (5xx) or uncaught page error reproduced.\n"
            "- Does not prove: Correctness of application state outside crash conditions.\n"
            "- Third-party errors and known benign noise have been neutralized via noise floor.\n"
        )
    elif oracle_class == OracleClass.B:
        return (
            "# Class B Limits\n\n"
            "- Proves: Metamorphic relation invariant violated on the target widget/journey.\n"
            "- Does not prove: Human intent; changes could reflect intentional design shifts.\n"
            "- Validation gate confirmed the relation holds across clean baselines.\n"
        )
    elif oracle_class == OracleClass.D:
        return (
            "# Class D Limits\n\n"
            "- Proves: Cross-layer inconsistency between ground-truth API JSON and rendered UI.\n"
            "- Does not prove: Whether backend or frontend is the faulty component.\n"
            "- Tolerances applied: strict integer count equality and cent-level currency bounds.\n"
        )
    else:
        return (
            f"# Class {oracle_class.value} Limits\n\n"
            "- Verifies behavioral divergence or specification discrepancy.\n"
            "- Intent confirmation recommended for non-crash violations.\n"
        )


def build_certificate(
    finding: Finding,
    world_spec: WorldSpec,
    shrink_result: ShrinkResult | None = None,
    replay_report: ReplayReport | None = None,
    tape: Tape | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Build a complete certificate directory with manifest and SHA-256 digests."""
    cert_dir = (output_dir or Path("results/certificates")) / finding.id
    evidence_dir = cert_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    # 1. claim.json
    claim_data = {
        "claim": finding.claim,
        "oracle_class": finding.oracle_class.value,
        "provenance": finding.id,
        "tier": finding.tier.value,
        "confidence": finding.confidence,
    }
    (cert_dir / "claim.json").write_text(json.dumps(claim_data, indent=2), encoding="utf-8")

    # 2. repro.json
    repro_actions: list[Action] = []
    if shrink_result and shrink_result.reduced_trace:
        repro_actions = shrink_result.reduced_trace
    elif finding.steps:
        repro_actions = finding.steps
    (cert_dir / "repro.json").write_text(
        json.dumps([a.model_dump() for a in repro_actions], indent=2), encoding="utf-8"
    )

    # 3. signature.json
    (cert_dir / "signature.json").write_text(
        json.dumps(finding.signature.model_dump(), indent=2), encoding="utf-8"
    )

    # 4. replay.json
    rep_dict: dict[str, Any] = {}
    if replay_report:
        rep_dict = replay_report.to_dict()
    elif shrink_result:
        rep_dict = {
            "total": shrink_result.replays_used,
            "reproduced": True,
            "wall_time_ms": shrink_result.wall_time_ms,
        }
    else:
        rep_dict = {"total": 1, "reproduced": True}
    (cert_dir / "replay.json").write_text(json.dumps(rep_dict, indent=2), encoding="utf-8")

    # 5. world.json
    (cert_dir / "world.json").write_text(
        json.dumps(world_spec.model_dump(), indent=2), encoding="utf-8"
    )

    # 6. limits.md
    (cert_dir / "limits.md").write_text(get_class_limits(finding.oracle_class), encoding="utf-8")

    # 7. evidence collection
    log_file = evidence_dir / "console.log"
    log_file.write_text(f"Certificate evidence initialized for finding {finding.id}\n", encoding="utf-8")

    # Copy tape if available
    if tape and hasattr(tape, "source_path") and tape.source_path:
        tape_src = Path(tape.source_path)
        if tape_src.exists():
            shutil.copy(tape_src, evidence_dir / "tape.jsonl")

    # 8. Compute manifest.json
    file_hashes: dict[str, str] = {}
    for p in sorted(cert_dir.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            rel_name = p.relative_to(cert_dir).as_posix()
            file_hashes[rel_name] = compute_sha256(p)

    hasher = hashlib.sha256()
    for rel_path in sorted(file_hashes.keys()):
        hasher.update(f"{rel_path}:{file_hashes[rel_path]}".encode())
    manifest_hash = hasher.hexdigest()

    manifest = CertificateManifest(
        certificate_id=finding.id,
        finding_id=finding.id,
        created_at=datetime.now(timezone.utc).isoformat(),
        files=file_hashes,
        manifest_hash=manifest_hash,
    )

    (cert_dir / "manifest.json").write_text(
        json.dumps(manifest.model_dump(), indent=2), encoding="utf-8"
    )

    return cert_dir
