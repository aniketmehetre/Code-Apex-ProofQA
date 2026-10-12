"""Acceptance tests for Phase 9 ProofBench runner, adjudicator, and metrics (Milestone M2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofbench.adjudicate import Adjudicator
from proofbench.metrics import compute_metrics, write_summary_and_reports
from proofbench.runner import BenchmarkRunner
from proofqa.contracts import (
    FailureSignature,
    Finding,
    OracleClass,
    Tier,
)


def test_adjudicator_identifies_true_bugs_and_duplicates() -> None:
    adjudicator = Adjudicator()

    sig_b01 = FailureSignature(
        kind="http_5xx",
        first_party_endpoint="/api/cart",
        status=500,
        error_type="ZeroQuantityException",
        message_norm="ZeroQuantityException",
    )
    finding = Finding(
        id="f_test_b01",
        oracle_class=OracleClass.A,
        tier=Tier.VERIFIED,
        signature=sig_b01,
        claim="Zero quantity cart addition returns 500",
    )

    credited: set[str] = set()

    # First sighting -> true_bug
    status, bid = adjudicator.adjudicate(finding, credited)
    assert status == "true_bug"
    assert bid == "B01"

    credited.add("B01")

    # Second sighting -> duplicate
    status, bid = adjudicator.adjudicate(finding, credited)
    assert status == "duplicate"
    assert bid == "B01"


def test_adjudicator_identifies_decoy_anomalies() -> None:
    adjudicator = Adjudicator()
    sig_d01 = FailureSignature(
        kind="http_4xx",
        first_party_endpoint="/api/decoy/not-found",
        status=404,
        message_norm="Friendly 404 page",
    )
    finding = Finding(
        id="f_decoy_hit",
        oracle_class=OracleClass.A,
        tier=Tier.SUSPECTED,
        signature=sig_d01,
        claim="Decoy friendly 404",
    )
    status, bid = adjudicator.adjudicate(finding, set())
    assert status == "decoy_hit"


def test_compute_metrics_and_write_summary(tmp_path: Path) -> None:
    fake_runs = [
        {
            "seed": 42,
            "adjudicated_outcomes": [{"status": "true_bug", "bug_id": "B01"}],
            "certificates": [{"verdict": "VALID"}],
            "replays_total": 1,
            "replays_success": 1,
            "shrink_orig_steps": 10,
            "shrink_reduced_steps": 3,
        }
    ]

    summary = compute_metrics(fake_runs, total_ground_truth_bugs=10)
    assert summary["true_bugs_count"] == 1
    assert summary["precision"] == 1.0
    assert summary["recall"] == 0.1
    assert summary["certificate_validity_rate"] == 1.0
    assert summary["average_shrink_reduction_pct"] == 70.0

    write_summary_and_reports(summary, output_dir=tmp_path)
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "report.md").exists()

    saved_summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert saved_summary["precision"] == 1.0


@pytest.mark.asyncio
async def test_benchmark_runner_executes_seeds(tmp_path: Path) -> None:
    runner = BenchmarkRunner(
        seeds=[42],
        results_dir=tmp_path / "results",
        output_file=tmp_path / "results" / "runs.jsonl",
    )
    summary = await runner.run()

    assert summary["true_bugs_count"] >= 1
    assert summary["certificate_validity_rate"] == 1.0
    assert (tmp_path / "results" / "runs.jsonl").exists()
    assert (tmp_path / "results" / "summary.json").exists()
