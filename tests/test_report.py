"""Tests for Prompt 9: Finding clustering, certificate report generation, and run reports.

Verifies:
1. Finding clustering groups duplicate signatures, keeps minimal trace, and tracks occurrence counts.
2. Certificate report for demo/recorded/recorded_b01 matches repro.json step for step.
3. CLI proofqa report writes report.md outside the certificate directory.
4. Run reports generate valid Markdown and JSON coverage artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from proofqa.cert.cluster import cluster_findings
from proofqa.cert.report import (
    action_to_plain_english,
    generate_certificate_report,
    generate_run_report,
)
from proofqa.cli import app
from proofqa.contracts import (
    Action,
    ActionKind,
    FailureSignature,
    Finding,
    Locator,
    OracleClass,
    Tier,
)


def test_finding_clustering_synthetic_double_find():
    """Prompt 9 Task 1: Cluster findings by signature, retain minimal trace, and count occurrences."""
    sig = FailureSignature(
        kind="http_5xx",
        first_party_endpoint="/api/cart",
        status=500,
        message_norm="ZeroQuantityException",
    )

    # Longer trace: 4 steps
    f1 = Finding(
        id="f1_long",
        oracle_class=OracleClass.A,
        tier=Tier.VERIFIED,
        signature=sig,
        claim="Zero quantity cart addition returns 500",
        steps=[
            Action(id="a0", kind=ActionKind.GOTO, value="/"),
            Action(id="a1", kind=ActionKind.CLICK, locator=Locator(role="button", name="Shop")),
            Action(id="a2", kind=ActionKind.FILL, locator=Locator(name="qty"), value="0"),
            Action(id="a3", kind=ActionKind.CLICK, locator=Locator(name="add")),
        ],
        confidence=0.9,
    )

    # Shorter trace: 2 steps (same underlying bug)
    f2 = Finding(
        id="f2_short",
        oracle_class=OracleClass.A,
        tier=Tier.VERIFIED,
        signature=sig,
        claim="Zero quantity cart addition returns 500",
        steps=[
            Action(id="a0", kind=ActionKind.GOTO, value="/"),
            Action(id="a1", kind=ActionKind.CLICK, locator=Locator(name="add")),
        ],
        confidence=1.0,
    )

    # Different bug
    sig_diff = FailureSignature(
        kind="http_5xx",
        first_party_endpoint="/api/checkout",
        status=500,
        message_norm="CheckoutException",
    )
    f3 = Finding(
        id="f3_other",
        oracle_class=OracleClass.A,
        tier=Tier.VERIFIED,
        signature=sig_diff,
        claim="Checkout failure",
        steps=[Action(id="b0", kind=ActionKind.GOTO, value="/checkout")],
        confidence=1.0,
    )

    clusters = cluster_findings([f1, f2, f3])

    assert len(clusters) == 2, f"Expected 2 clusters, got {len(clusters)}"

    # Find the cluster for the first bug
    cart_cluster = next(c for c in clusters if c.finding.signature.first_party_endpoint == "/api/cart")
    assert cart_cluster.occurrences == 2
    assert cart_cluster.minimal_trace_length == 2
    assert cart_cluster.finding.id == "f2_short"


def test_certificate_report_golden_file_step_for_step(tmp_path: Path):
    """Prompt 9 Task 2 & 5: Golden test ensuring demo_b01 report matches repro.json step for step."""
    cert_dir = Path(__file__).resolve().parent.parent / "demo" / "recorded" / "recorded_b01"
    assert cert_dir.exists()

    repro_raw = json.loads((cert_dir / "repro.json").read_text(encoding="utf-8"))
    actions = [Action.model_validate(a) for a in repro_raw]

    out_file = tmp_path / "golden_b01_report.md"
    report_text = generate_certificate_report(cert_dir, output_path=out_file)

    assert out_file.exists()
    assert "[Class A]" in report_text
    assert "repro.json" not in report_text  # Clean user-facing output
    assert "proofqa verify" in report_text

    # Verify each step from repro.json is translated in order
    for idx, act in enumerate(actions, start=1):
        expected_step = action_to_plain_english(act)
        assert f"{idx}. {expected_step}" in report_text


def test_cli_report_command(tmp_path: Path):
    """Prompt 9 Task 2 & 4: CLI proofqa report writes report.md outside sealed certificate directory."""
    runner = CliRunner()
    cert_dir = Path(__file__).resolve().parent.parent / "demo" / "recorded" / "recorded_b01"
    out_dest = tmp_path / "cli_generated_report.md"

    result = runner.invoke(app, ["report", str(cert_dir), "--out", str(out_dest)])
    assert result.exit_code == 0
    assert out_dest.exists()
    assert "Defect Overview" in out_dest.read_text(encoding="utf-8")


def test_run_report_generation(tmp_path: Path):
    """Prompt 9 Task 3: generate_run_report produces run_report.md and run_report.json."""
    run_dir = tmp_path / "run_01"
    run_data = {
        "findings": ["B01", "B09"],
        "coverage": {
            "pages_visited": 4,
            "semantic_states": 12,
            "controls_exercised": 28,
            "probes_fired": {"boundary": 8, "burst": 5, "reload": 3},
        },
        "suppressed_noise": {
            "third_party_errors": 2,
            "friendly_404s": 5,
            "masked_banners": 1,
        },
        "unresolved": {
            "client_blocked": 1,
            "timeouts": 0,
        },
    }

    report_md, report_json = generate_run_report(run_dir, run_data)

    assert (run_dir / "run_report.json").exists()
    assert (run_dir / "run_report.md").exists()
    assert report_json["coverage"]["pages_visited"] == 4
    assert report_json["suppressed_noise"]["friendly_404s"] == 5
    assert "**Client-Side Validation Blocks:** 1" in report_md
