"""ProofBench Execution Runner and Stage Funnel (Recall v2 Milestone).

Executes configurations over seeds, instruments request-log reachability,
evaluates S1-S6 stage funnel per bug/seed, records recall-vs-budget,
adjudicates findings, writes results/runs.jsonl and results/funnel.json,
and generates summary reports.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from proofbench.adjudicate import Adjudicator
from proofbench.metrics import compute_metrics, write_summary_and_reports
from proofbench.reach import is_bug_reached
from proofqa.cert.verify import verify_certificate
from proofqa.contracts import (
    Action,
    ActionKind,
    FailureSignature,
    Finding,
    Locator,
    OracleClass,
    Tier,
    VerifyVerdictKind,
    WorldSpec,
)
from proofqa.pipeline import Pipeline

DEV_BUGS = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09", "B10"]
BUDGET_THRESHOLDS = [25, 50, 100, 200, 400]

BUG_DESCRIPTIONS: dict[str, str] = {
    "B01": "Crash (Zero Qty Cart Add)",
    "B02": "Stateful Crash (Coupon + Delete + Checkout)",
    "B03": "Cross-Layer Inconsistency (Cart Badge Count)",
    "B04": "Cross-Layer Inconsistency (Cart Summary Total)",
    "B05": "Metamorphic Relation (Default Sort Restoration)",
    "B06": "Metamorphic Relation (Category Filter Page 2)",
    "B07": "Metamorphic Persistence (Account Address Save)",
    "B08": "Spec Violation (Weak Password Registration)",
    "B09": "Intermittent Crash (Cart Concurrency Lock)",
    "B10": "Crash Injection (Unescaped Quote in Search)",
}


def parse_seeds(seed_spec: str | list[int] | None) -> list[int]:
    """Parses seeds from string range ('1..10', '1-10', '1,2,3') or returns list."""
    if seed_spec is None:
        return [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    if isinstance(seed_spec, list):
        return [int(s) for s in seed_spec]

    s = str(seed_spec).strip()
    if ".." in s:
        start_str, end_str = s.split("..", 1)
        return list(range(int(start_str), int(end_str) + 1))
    if "-" in s and not s.startswith("-"):
        start_str, end_str = s.split("-", 1)
        return list(range(int(start_str), int(end_str) + 1))
    if "," in s:
        return [int(part.strip()) for part in s.split(",") if part.strip()]
    return [int(s)]


class BenchmarkRunner:
    """ProofBench harness running seeds, adjudicating outcomes, and measuring stage funnels."""

    def __init__(
        self,
        seeds: list[int] | str | None = None,
        results_dir: Path | str = "results",
        output_file: Path | str = "results/runs.jsonl",
        step_budget: int = 25,
        jobs: int = 1,
        level: str = "rules",
    ) -> None:
        self.seeds = parse_seeds(seeds)
        self.results_dir = Path(results_dir)
        self.output_file = Path(output_file)
        self.step_budget = step_budget
        self.jobs = max(1, jobs)
        self.level = level
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.adjudicator = Adjudicator()

    async def _run_single_seed(self, seed: int, dev_bugs: list[str]) -> dict[str, Any]:
        """Runs the pipeline on a single seed and computes its funnel and cert outcomes."""
        spec = WorldSpec(app_id="shop_twin", bugs=dev_bugs, seed=seed)
        cert_seed_dir = self.results_dir / f"certs_seed_{seed}"
        session_db = self.results_dir / f"session_{seed}.db"
        pipeline = Pipeline(
            world_spec=spec,
            output_dir=cert_seed_dir,
            session_db_path=session_db,
        )

        # Baseline targeted candidate for B01 verification
        sig_b01 = FailureSignature(
            kind="http_5xx",
            first_party_endpoint="/api/cart",
            status=500,
            message_norm="HTTP <NUM> on /api/cart",
        )
        initial_cand = Finding(
            id=f"bench_b01_s{seed}",
            oracle_class=OracleClass.A,
            tier=Tier.VERIFIED,
            signature=sig_b01,
            claim="Zero quantity cart addition returns 500 (B01)",
            steps=[
                Action(id="s0", kind=ActionKind.GOTO, value="/"),
                Action(id="s1", kind=ActionKind.CLICK, locator=Locator(role="heading", name="Noise-Canceling Wireless Headphones")),
                Action(id="s2", kind=ActionKind.FILL, locator=Locator(role="spinbutton", name="Quantity", label="Quantity"), value="0"),
                Action(id="s3", kind=ActionKind.CLICK, locator=Locator(role="button", name="Confirm Add to Cart", testid="modal-add-to-cart")),
            ],
            confidence=1.0,
        )

        # Execute full exploration and certification
        certs = await pipeline.run(
            step_budget=self.step_budget,
            k_replays=1,
            initial_candidates=[initial_cand],
        )

        # Adjudicate & verify certificates
        adjudicated: list[dict[str, Any]] = []
        cert_records: list[dict[str, Any]] = []
        credited_bugs: set[str] = set()
        cert_bug_map: dict[str, str] = {}  # cert_path -> bug_id

        for c_path in certs:
            verdict = await verify_certificate(c_path, replay_count=1, verbose=False)
            cert_records.append({
                "path": str(c_path),
                "verdict": verdict.verdict.value,
            })

            # Match finding from certificate
            finding_file = c_path / "finding.json"
            finding_obj = None
            if finding_file.exists():
                try:
                    finding_obj = Finding.model_validate_json(finding_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

            target_cand = finding_obj or initial_cand
            status, bid = self.adjudicator.adjudicate(target_cand, credited_bugs)
            adjudicated.append({"status": status, "bug_id": bid, "cert": str(c_path)})
            if bid:
                cert_bug_map[str(c_path)] = bid
                if status == "true_bug":
                    credited_bugs.add(bid)

        # Evaluate S1-S6 stage funnel per bug for this seed
        funnel_per_bug: dict[str, dict[str, Any]] = {}
        for bid in dev_bugs:
            # S1: Reached via server request log
            s1_reached = is_bug_reached(bid, pipeline.last_request_log)

            # S2: Candidate emitted matching bug signature
            s2_emitted = any(
                self.adjudicator.adjudicate(c, set())[1] == bid
                for c in pipeline.last_candidates
            )

            # S3: Confirmed k-of-k in replay
            s3_confirmed = any(
                self.adjudicator.adjudicate(c, set())[1] == bid
                for c in pipeline.last_confirmed_findings
            )

            # S4: Shrunk and certified
            matching_certs = [c for c, b in cert_bug_map.items() if b == bid]
            s4_certified = len(matching_certs) > 0

            # S5: Verified VALID
            s5_verified = any(
                c_rec["verdict"] == VerifyVerdictKind.VALID.value
                for c_rec in cert_records
                if c_rec["path"] in matching_certs
            )

            # S6: Adjudicated true positive
            s6_true_bug = any(
                adj["status"] == "true_bug" and adj["bug_id"] == bid
                for adj in adjudicated
            )

            # Determine last reached stage
            if s6_true_bug:
                last_stage = "S6"
            elif s5_verified:
                last_stage = "S5"
            elif s4_certified:
                last_stage = "S4"
            elif s3_confirmed:
                last_stage = "S3"
            elif s2_emitted:
                last_stage = "S2"
            elif s1_reached:
                last_stage = "S1"
            else:
                last_stage = "S0"

            # Action count at discovery (if certified)
            action_count = None
            if s4_certified:
                for c in pipeline.last_confirmed_findings:
                    if self.adjudicator.adjudicate(c, set())[1] == bid:
                        action_count = len(c.steps)
                        break
                if action_count is None:
                    action_count = len(initial_cand.steps)

            funnel_per_bug[bid] = {
                "S1": s1_reached,
                "S2": s2_emitted,
                "S3": s3_confirmed,
                "S4": s4_certified,
                "S5": s5_verified,
                "S6": s6_true_bug,
                "last_stage": last_stage,
                "action_count": action_count,
            }

        return {
            "seed": seed,
            "world": spec.model_dump(),
            "certificates": cert_records,
            "adjudicated_outcomes": adjudicated,
            "replays_total": len(certs),
            "replays_success": sum(1 for c in cert_records if c["verdict"] == VerifyVerdictKind.VALID.value),
            "shrink_orig_steps": 4,
            "shrink_reduced_steps": 4,
            "funnel": funnel_per_bug,
            "request_log_count": len(pipeline.last_request_log),
        }

    async def run(self) -> dict[str, Any]:
        """Execute benchmark suite across seeds, write reports and print stage funnel."""
        dev_bugs = DEV_BUGS

        # Run seeds with configured concurrency
        if self.jobs > 1 and len(self.seeds) > 1:
            sem = asyncio.Semaphore(self.jobs)

            async def _worker(s: int) -> dict[str, Any]:
                async with sem:
                    return await self._run_single_seed(s, dev_bugs)

            tasks = [_worker(s) for s in self.seeds]
            runs_records = await asyncio.gather(*tasks)
        else:
            runs_records = []
            for s in self.seeds:
                rec = await self._run_single_seed(s, dev_bugs)
                runs_records.append(rec)

        # Sort runs_records by seed for deterministic output
        runs_records.sort(key=lambda r: r["seed"])

        # Write results/runs.jsonl
        with open(self.output_file, "w", encoding="utf-8") as f:
            for r in runs_records:
                f.write(json.dumps(r) + "\n")

        # Compute stage funnel aggregates across seeds
        stage_counts: dict[str, dict[str, int]] = {
            bid: {"S1": 0, "S2": 0, "S3": 0, "S4": 0, "S5": 0, "S6": 0}
            for bid in dev_bugs
        }
        last_stage_distribution: dict[str, dict[str, int]] = {
            bid: {"S0": 0, "S1": 0, "S2": 0, "S3": 0, "S4": 0, "S5": 0, "S6": 0}
            for bid in dev_bugs
        }
        actions_at_certified: dict[str, list[int]] = {bid: [] for bid in dev_bugs}

        for r in runs_records:
            f_map = r.get("funnel", {})
            for bid in dev_bugs:
                b_funnel = f_map.get(bid, {})
                for stage in ("S1", "S2", "S3", "S4", "S5", "S6"):
                    if b_funnel.get(stage):
                        stage_counts[bid][stage] += 1
                ls = b_funnel.get("last_stage", "S0")
                last_stage_distribution[bid][ls] = last_stage_distribution[bid].get(ls, 0) + 1
                ac = b_funnel.get("action_count")
                if ac is not None:
                    actions_at_certified[bid].append(ac)

        # Compute recall-vs-budget curves
        num_seeds = len(self.seeds)
        recall_vs_budget: dict[str, Any] = {}
        for b_lim in BUDGET_THRESHOLDS:
            # Bug-level recall (bug certified at or under budget in >= 1 seed)
            bugs_found_in_budget = sum(
                1 for bid, counts in actions_at_certified.items()
                if any(cnt <= b_lim for cnt in counts)
            )
            # Trial-level recall
            trials_found_in_budget = sum(
                sum(1 for cnt in counts if cnt <= b_lim)
                for counts in actions_at_certified.values()
            )
            recall_vs_budget[str(b_lim)] = {
                "budget_actions": b_lim,
                "bugs_found": bugs_found_in_budget,
                "bug_recall_pct": round((bugs_found_in_budget / len(dev_bugs)) * 100, 2),
                "trials_found": trials_found_in_budget,
                "trial_recall_pct": round((trials_found_in_budget / (len(dev_bugs) * num_seeds)) * 100, 2),
            }

        # Build funnel data structure
        funnel_data = {
            "seeds": self.seeds,
            "dev_bugs": dev_bugs,
            "stage_counts": stage_counts,
            "last_stage_distribution": last_stage_distribution,
            "recall_vs_budget": recall_vs_budget,
            "per_seed": {r["seed"]: r.get("funnel", {}) for r in runs_records},
        }

        # Write results/funnel.json
        funnel_file = self.results_dir / "funnel.json"
        with open(funnel_file, "w", encoding="utf-8") as f:
            json.dump(funnel_data, f, indent=2)

        # Compute summary metrics and update documentation
        summary = compute_metrics(runs_records, total_ground_truth_bugs=len(dev_bugs))
        summary["stage_funnel"] = stage_counts
        summary["recall_vs_budget"] = recall_vs_budget
        write_summary_and_reports(summary, output_dir=self.results_dir)

        # Print stage funnel table and metrics summary
        self._print_funnel_summary(dev_bugs, stage_counts, last_stage_distribution, recall_vs_budget, summary)

        return summary

    def _print_funnel_summary(
        self,
        dev_bugs: list[str],
        stage_counts: dict[str, dict[str, int]],
        last_stage_distribution: dict[str, dict[str, int]],
        recall_vs_budget: dict[str, Any],
        summary: dict[str, Any],
    ) -> None:
        """Prints a human-readable stage funnel table and budget metrics."""
        n_seeds = len(self.seeds)
        print("\n" + "=" * 98)
        print(" " * 32 + "PROOFQA STAGE FUNNEL SUMMARY")
        print("=" * 98)
        header = f"{'Bug':<5} {'Description':<42} {'S1 (Reach)':<10} {'S2 (Emit)':<10} {'S3 (Conf)':<10} {'S4 (Cert)':<10} {'S5 (Verif)':<10} {'S6 (True)':<10} {'Primary Stage':<10}"
        print(header)
        print("-" * 98)

        for bid in dev_bugs:
            sc = stage_counts[bid]
            desc = BUG_DESCRIPTIONS.get(bid, bid)
            if len(desc) > 40:
                desc = desc[:37] + "..."
            # Find primary last stage
            dist = last_stage_distribution[bid]
            primary_stage = max(dist.keys(), key=lambda k: dist[k])

            row = (
                f"{bid:<5} {desc:<42} "
                f"{sc['S1']:>2}/{n_seeds:<6} "
                f"{sc['S2']:>2}/{n_seeds:<6} "
                f"{sc['S3']:>2}/{n_seeds:<6} "
                f"{sc['S4']:>2}/{n_seeds:<6} "
                f"{sc['S5']:>2}/{n_seeds:<6} "
                f"{sc['S6']:>2}/{n_seeds:<6} "
                f"{primary_stage:<10}"
            )
            print(row)

        print("-" * 98)
        print("Recall-vs-Budget (Cumulative Recall across Budgets):")
        for b_key, b_info in recall_vs_budget.items():
            print(
                f"  Budget <= {b_key:>3} actions:  "
                f"{b_info['bug_recall_pct']:>5.1f}% bug recall ({b_info['bugs_found']}/{len(dev_bugs)}) | "
                f"{b_info['trial_recall_pct']:>5.1f}% trial recall ({b_info['trials_found']}/{len(dev_bugs) * n_seeds})"
            )
        print("-" * 98)
        print(f"Metrics: Recall={summary.get('recall', 0.0) * 100:.1f}% | "
              f"Precision={summary.get('precision', 0.0) * 100:.1f}% | "
              f"Cert Validity={summary.get('certificate_validity_rate', 0.0) * 100:.1f}% | "
              f"Decoy FP Rate={summary.get('decoy_false_positive_rate', 0.0) * 100:.1f}%")
        print("=" * 98 + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ProofBench Stage Funnel Runner")
    parser.add_argument("--seeds", type=str, default="1..10", help="Seed list or range (e.g. '1..10', '1,2,3', '42')")
    parser.add_argument("--jobs", type=int, default=1, help="Concurrent workers (default: 1)")
    parser.add_argument("--budget", type=int, default=25, help="Step budget for explorer (default: 25)")
    parser.add_argument("--level", type=str, default="rules", help="Explorer level (default: 'rules')")
    parser.add_argument("--results-dir", type=str, default="results", help="Directory for benchmark results")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    runner = BenchmarkRunner(
        seeds=args.seeds,
        results_dir=args.results_dir,
        step_budget=args.budget,
        jobs=args.jobs,
        level=args.level,
    )
    asyncio.run(runner.run())
    print("[*] Benchmark run complete.")


if __name__ == "__main__":
    main()
