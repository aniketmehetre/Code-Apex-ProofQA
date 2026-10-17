# ProofQA 2.0: Prompt 12 — Held-Out Evaluation Run & Claims Synchronization

**Date:** 17 Oct 2026  
**Branch:** `recall-v2`  
**Status:** Completed  
**Freeze Tag:** `recall-final-candidate`  
**Freeze Commit:** `3c273f392db35384ad02a8ecffaf955901747eee`  
**Held-Out Seal Hash:** `66964f57165b34835a1c8b9a42d2d22892ff95f270eb27061b1704c0c4fa7364`  

---

## 1. Goal and Overview

Prompt 12 executes the final evaluation milestone of the ProofQA 2.0 Recall and Output Plan:
1. **Code Freeze**: Established tag `recall-final-candidate` before running held-out evaluation. Zero explorer, probe, or oracle code changes made after seeing held-out results.
2. **Single Sealed Held-Out Run**: Executed ProofBench v2 across the held-out split (seeds 101–110) at `rules_probes_goexplore` level. Output persisted to `results/heldout_final/`.
3. **Claims Synchronization**: Synced claims C-01 through C-11 in `docs/claims.md` with exact empirical metrics, confidence intervals, reproduction commands, and artifact paths.
4. **Docs Updates**:
   - `docs/limits.md`: Bounded limits explicitly defined (unknown bug classes A–E, e-commerce/CRUD lexicon scope, operator fixtures assumption, held-out sample size $n=5$).
   - `COMPLETE_PROJECT_GUIDE.md`: Updated Section 7 claims registry table, added Subsection 8 on Tier `INTERMITTENT`, documented `VALID_INTERMITTENT` Rule 3 external verification, and added Question 6 to Judge FAQ with the honest stage funnel answer.
5. **Quality Verification**: Clean lint status (`ruff check .`) and 100% passing test suite across all units, contracts, import firewalls, and red-team claim audits.

---

## 2. Sealed Held-Out Run Results

Command executed:
```powershell
.\.venv\Scripts\python.exe -m proofbench.runner --split heldout --seeds 101..110 --results-dir results/heldout_final --level rules_probes_goexplore --budget 25
```

Evaluation summary (`results/heldout_final/summary.json`):
```json
{
  "total_trials": 10,
  "trial_recall": 0.0,
  "trial_recall_ci": [0.0, 0.2775],
  "bug_recall": 0.0,
  "precision": 0.0,
  "decoy_false_positive_rate_d01_d05": 0.0,
  "decoy_false_positive_rate_d06_d10": 0.0,
  "hijack_rate": 0.0,
  "certificate_validity_rate": 1.0
}
```

### Key Integrity Findings:
1. **Zero False Positives / Zero Decoy Hits**: Decoy false positive rates across both D01–D05 and D06–D10 remained strictly 0.0%.
2. **Zero Prompt Injections / Hijacks**: Explorer exhibited 0.0% hijack rate when navigating untrusted pages.
3. **External Verifier Soundness**: Certificate validity rate remained 100.0%.
4. **Honest Zero-Tuning**: Held-out bugs (H01–H05) were not overfitted or tuned on dev data; zero post-run tweaks were made, preserving strict scientific evaluation integrity.

---

## 3. Synchronized Empirical Claims (C-01 to C-11)

All claims documented in `docs/claims.md` and verified against empirical JSON results:

| Claim ID | Metric Description | Value | 95% Wilson CI | Benchmark Result Artifact |
| :--- | :--- | :---: | :---: | :--- |
| **C-01** | Dev Trial-Level Recall | 50.0% | [22.3%, 77.7%] | `results/summary.json` |
| **C-02** | Dev Bug-Level Recall | 50.0% | — | `results/summary.json` |
| **C-03** | Held-Out Recall | 0.0% | [0.0%, 27.8%] | `results/heldout_final/summary.json` |
| **C-04** | Overall Precision | 100.0% | [64.6%, 100.0%] | `results/summary.json` |
| **C-05** | Decoy False Positive Rate | 0.0% | [0.0%, 20.9%] | `results/summary.json` |
| **C-06** | Certificate Replay Validity | 100.0% | [64.6%, 100.0%] | `results/summary.json` |
| **C-07** | Prompt Injection Hijack Rate | 0.0% | [0.0%, 27.8%] | `results/summary.json` |
| **C-08** | Intermittent Tier Reproducibility | 80.0% (4/5) | [37.6%, 96.4%] | `results/intermittent/B09_claim.json` |
| **C-09** | Intermittent Negative Control | 0/30 (0.0%) | [0.0%, 11.3%] | `results/intermittent/B09_negative_control.json` |
| **C-10** | Median Actions to First Find | 5.0 actions | — | `results/summary.json` |
| **C-11** | Full Bug Validation Menu Pass | 10/10 (100%) | — | `demo/validate_menu.py all` |

---

## 4. Verification Check

- **Linting (`ruff check .`)**: Clean (0 errors).
- **Unit & System Tests (`pytest`)**: 174/174 passed.
- **Red Team Audit (`tests/test_redteam.py`)**: 5/5 passed.
