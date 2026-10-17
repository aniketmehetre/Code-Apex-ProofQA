# ProofQA 2.0: Prompt 10 — Bench v2, Dashboard Views, and Blind Demo

**Date:** 17 Oct 2026  
**Branch:** `recall-v2`  
**Status:** Completed  

---

## 1. Goal and Overview

Prompt 10 delivers the empirical benchmarking infrastructure (ProofBench v2), user-facing dashboards, the full judge's validation menu (10/10 flags), and the live blind discovery demo with recorded replay fallback.

Key requirements fulfilled:
1. **Bench v2 Reporting (`proofbench/runner.py`, `proofbench/metrics.py`)**:
   - Dev split ($B01-B10$, seeds $1-10$) and Held-out split ($H01-H05$, seeds $101-110$) separated cleanly.
   - Dual recall reporting: Trial-level (bug $\times$ seed) with Wilson 95% confidence intervals AND Bug-level recall (detected in $\ge 50\%$ seeds).
   - Precision with 95% Wilson CI, decoy false positive separation ($D01-D05$ vs $D06-D10$), hijack rate, median actions, and time to first certificate.
   - Ablation ladder supporting `--level`: `monkey`, `rules`, `rules_probes`, `rules_probes_goexplore`, `full`, including `--no-fixtures` mode.
2. **Autonomous Blind Demo (`demo/demo_blind.py`, `make demo-blind`)**:
   - ProofQA explores Shop Twin with dev bugs enabled and zero hints.
   - Streams live progress, certifies discovered defects, and executes independent Rule 3 verification.
   - Event cache saved to `results/demo_blind_cache/events.json` with `< 5s` playback via `--replay-recorded`.
   - Execution finishes under 3 minutes (measured ~83s on local runtime).
3. **Judge's-Choice Validation Menu (`demo/validate_menu.py`, `make validate-menu`)**:
   - 10 of 10 bug flags ($B01-B10$) supported, certified, and independently verified with zero false positives.

---

## 2. Validation Menu Results: 10/10 Flags Passed (100%)

Command executed:
```powershell
.\.venv\Scripts\python.exe demo\validate_menu.py all
```

Outcome:
| Flag | Name | Class | Verifier Verdict | Adjudication | Result |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **B01** | Zero quantity cart addition returns 500 | A | `VALID` | `true_bug` (B01) | **PASS** |
| **B02** | Coupon dereference crash after item deletion | A | `VALID` | `true_bug` (B02) | **PASS** |
| **B03** | Cart badge count UI vs network divergence | D | `VALID` | `true_bug` (B03) | **PASS** |
| **B04** | Cart summary total ignores discount | D | `VALID` | `true_bug` (B04) | **PASS** |
| **B05** | Sort restoration metamorphic violation | B | `VALID` | `true_bug` (B05) | **PASS** |
| **B06** | Filter category fails on page 2 | B | `VALID` | `true_bug` (B06) | **PASS** |
| **B07** | Saved address loss upon page reload | B | `VALID` | `true_bug` (B07) | **PASS** |
| **B08** | Weak password allowed during registration | C | `VALID` | `true_bug` (B08) | **PASS** |
| **B09** | Transient concurrency lock timeout | A | `VALID_INTERMITTENT` | `true_bug` (B09) | **PASS** |
| **B10** | Unescaped single quote SQL injection in search | A | `VALID` | `true_bug` (B10) | **PASS** |

**Summary: 10 of 10 flags passed (100% pass rate).**

---

## 3. Autonomous Blind Demo (`demo/demo_blind.py`)

### Live Run
```powershell
.\.venv\Scripts\python.exe demo\demo_blind.py
```
- **Autonomous Discovery**: Discovered SQL injection via boundary probe on search (`'`) $\to$ HTTP 500 on `/api/products` (B10).
- **Certificate Issued**: `results\demo_blind_certs\finding_A_23e7bf51`
- **Rule 3 Verification**: Passed independent verification with verdict `VALID`.
- **Runtime**: 83.1s (well within the 3-minute presentation limit).

### Recorded Fallback Mode
```powershell
.\.venv\Scripts\python.exe demo\demo_blind.py --replay-recorded
```
- Replays cached event stream from `results/demo_blind_cache/events.json`.
- Clearly labelled as `[RECORDED RUN]`.
- Completes in ~1s for deterministic, zero-risk live stage demos.

---

## 4. Architectural Rules & Integrity Guard Checks

- **Rule 3 Isolation**: `proofqa/cert/verify.py` contains zero imports from `proofqa.explore`, `proofqa.oracles`, `proofqa.llm`, `proofqa.uncertainty`, or `proofqa.spec`. Verified by `tests/test_import_guards.py`.
- **Root Navigation Safety**: Action traces initialized with `GOTO /` ensuring isolated browser contexts in replay and verification never stall on `about:blank`.
- **Zero Decoy False Positives**: Decoys $D01-D10$ remain unflagged across all runs.
