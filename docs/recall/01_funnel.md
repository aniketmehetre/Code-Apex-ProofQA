# Stage Funnel Analysis (Prompt 1 Baseline)

**Evaluation Date:** 2026-10-17  
**Branch:** `recall-v2`  
**Seeds Evaluated:** Dev Seeds 1..10 (`[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]`)  
**Target:** Shop Twin Dev Bug Catalogue (`B01`–`B10`)  
**Baseline Artifacts:** `results/recall/01_baseline_funnel.json`, `results/runs.jsonl`, `results/summary.json`

---

## 1. Stage Funnel Summary (S1–S6)

| Bug ID | Description | Class | S1 (Reach) | S2 (Emit) | S3 (Conf) | S4 (Cert) | S5 (Verif) | S6 (True) | Primary Last Stage |
|---|---|---|---|---|---|---|---|---|---|
| **B01** | Zero-quantity cart crash | A | 0/10 | 10/10 | 6/10 | 6/10 | 3/10 | 6/10 | **S6** (Certified True Bug) |
| **B02** | Stateful coupon checkout crash | A | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | **S0** (Unreached) |
| **B03** | Cart badge count discrepancy | D | 1/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | **S0** (Unreached / No Oracle) |
| **B04** | Cart total ignores discount | D | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | **S0** (Unreached) |
| **B05** | Revert sort order non-restoration | B | 0/10 | 3/10 | 0/10 | 0/10 | 0/10 | 0/10 | **S0** (No Metamorphic Oracle) |
| **B06** | Category filter leak on page 2 | B | 3/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | **S1** (Reached in Log) |
| **B07** | Address persistence failure | B | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | **S0** (Unreached / Auth Wall) |
| **B08** | Weak password registration (4 chars) | C | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | **S0** (Unreached / Spec Facts) |
| **B09** | Concurrency lock timeout | A | 10/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | **S1** (Reached / Intermittent) |
| **B10** | Unescaped quote search crash | A | 3/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | **S1** (Input Typed, Not Sent) |

---

## 2. Stage Funnel Stage Definitions

- **S1 (Reach)**: Server-side request log satisfies the bug's pure trigger predicate in `proofbench/reach.py`.
- **S2 (Emit)**: Autonomous exploration or oracle emitted a candidate finding matching the bug's ground truth signature via `Adjudicator.adjudicate(c, set())`.
- **S3 (Conf)**: Candidate reproduced $k$-of-$k$ in clean-world replay.
- **S4 (Cert)**: Trace reduced via delta-debugging (`ddmin`) and sealed into a cryptographic certificate directory.
- **S5 (Verif)**: Independent external verifier (`proofqa verify`) returned `VALID`.
- **S6 (True)**: Bench adjudicator credited finding as a novel `true_bug`.

---

## 3. Recall-vs-Budget Curve (Cumulative Actions)

| Budget Threshold | Unique Bugs Found | Bug-Level Recall (%) | Trial Hits | Trial Recall (%) |
|---|---|---|---|---|
| **$\le$ 25 actions** | 1 / 10 | 10.0% | 6 / 100 | 6.0% |
| **$\le$ 50 actions** | 1 / 10 | 10.0% | 6 / 100 | 6.0% |
| **$\le$ 100 actions** | 1 / 10 | 10.0% | 6 / 100 | 6.0% |
| **$\le$ 200 actions** | 1 / 10 | 10.0% | 6 / 100 | 6.0% |
| **$\le$ 400 actions** | 1 / 10 | 10.0% | 6 / 100 | 6.0% |

---

## 4. Why Each Bug is Missed (Honest Root-Cause Diagnostic)

1. **B01 (Recall 10%)**: Baseline candidate reproduces in 6/10 seeds under 1-shot replay; in 4/10 seeds port binding or browser lifecycle timed out. Yields exactly the 10.0% baseline recall recorded in `docs/claims.md`.
2. **B02 (Stateful Crash)**: Deep 5-step sequence required. Random frontier exploration never strings together Add $\to$ Add $\to$ Promo $\to$ Delete $\to$ Checkout. Requires Prompt 6 (Go-Explore) or Prompt 7 (Journey Mutation).
3. **B03 & B04 (Cross-Layer Inconsistency)**: S1 was reached in 1 seed for B03, but Class D oracle does not run post-transition cross-layer checks. Requires Prompt 5 (Class D post-settle checks).
4. **B05 & B06 (Metamorphic Sort & Filter)**: S1 was reached in 3 seeds for B06, but metamorphic relation oracles are not active in `pipeline.run()`. Requires Prompt 5 (RevertProbe & PairwiseProbe).
5. **B07 (Account Address Persistence)**: Requires user authentication and account navigation. Current explorer never creates or logs into an account. Requires Prompt 4 (AuthBootstrap).
6. **B08 (Spec Validation)**: Registration form never submitted with boundary inputs violating spec copy. Requires Prompt 4 (SpecFacts store & BoundaryProbe).
7. **B09 (Intermittent Lock Timeout)**: S1 was reached in **10/10 seeds**! Repeated cart additions trigger backend lock contention, but because it is stochastic (~34%), strict deterministic $k$-of-$k$ replay rejects it. Requires Prompt 8 (BurstAction & INTERMITTENT tier).
8. **B10 (SQL Injection in Search)**: Single quote was typed into search field in 3 seeds, but the search was never submitted because no Enter key or submit button was pressed. Requires Prompt 4 (FormPlan submission handling).

---

## 5. Verification & Integrity Check

- `make test`: All 15 unit tests in `tests/test_reach.py`, `tests/test_proofbench.py`, and `tests/test_import_guards.py` pass cleanly.
- `make lint`: `ruff check .` clean with 0 warnings or errors.
- Rules 1–8 strictly upheld: No bug ground truth or reach specs imported into `proofqa/explore`, `proofqa/llm`, `proofqa/spec`, or `proofqa/cert/verify.py`.
