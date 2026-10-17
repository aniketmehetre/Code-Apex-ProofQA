# ProofQA 2.0: Prompt 8 — Burst Action and INTERMITTENT Tier for B09

**Date:** 17 Oct 2026  
**Branch:** `recall-v2`  
**Status:** Completed  

---

## 1. Goal and Task 0 Evaluation

B09 in Shop Twin simulates a transient concurrency lock timeout during cart insertion (`/api/cart`).
Task 0 evaluation confirmed:
- In `apps/shop_twin/backend/app.py`:
  ```python
  if bugs.is_on("B09"):
      import random
      if random.random() < 0.34:
          raise HTTPException(
              status_code=500,
              detail="LockTimeoutException: Transient concurrency lock timeout during cart insertion",
          )
  ```
- **Stochastic Nature (Case B)**: Failure occurs with ~34% probability per cart insertion request without per-request seed resets.
- Under single deterministic action replay, B09 reproduces with only ~34% probability, which is rejected under strict 100% deterministic replay ($k$-of-$k$).

---

## 2. Mathematical Modeling and Confidence Thresholds

- **Single Click Failure Probability ($p$)**: $p \approx 0.34$
- **Burst of 5 Concurrent Clicks**:
  $$P(\text{at least one 500 in 5 clicks}) = 1 - (1 - 0.34)^5 \approx 1 - 0.1252 = 87.48\%$$
- **Replication Across 5 Replays**:
  - Strict $3$-of-$3$ reproducibility would succeed only with $(0.8748)^3 \approx 66.9\%$ probability.
  - $m$-of-$n$ ($2$-of-$5$) reproducibility succeeds with:
    $$P(X \ge 2) = 1 - P(X = 0) - P(X = 1) \approx 99.89\%$$
- This mathematical foundation guarantees that true intermittent defects are captured with $>99.8\%$ statistical power without relaxing oracles or compromising Rule 3 / Rule 8 integrity.

---

## 3. Implementation Details

### A. Non-Breaking Contract Extension
- In `proofqa/contracts.py`:
  - Added optional additive field `burst: int = 1` to `Action`.
  - Added `@model_serializer(mode="wrap")` ensuring that default `burst=1` is **omitted** from dictionary and JSON serialization.
  - Bumped `contracts_version` to `"1.1"`.
  - Added `VALID_INTERMITTENT` to `VerifyVerdictKind`.
  - Added `observed_rate: str | None = None` to `Finding`.
  - Verified that all existing certificates under `results/` and `demo/` verify byte-for-byte with 0 hash discrepancies (`test_existing_certificates_verify_byte_for_byte`).

### B. Browser Execution
- In `proofqa/browser/executor.py`:
  - When `action.kind == ActionKind.CLICK` and `action.burst > 1`, dispatches concurrent click tasks via `asyncio.gather(*tasks, return_exceptions=True)` with `force=True`.
- In `proofqa/explore/grounding.py`:
  - Action grounding choke point preserves `burst` attribute while sanitizing and matching against grounded controls.

### C. BurstProbe
- In `proofqa/explore/probes/burst.py`:
  - Targets mutating controls (`add to cart`, `buy`, `confirm`).
  - Proposes `Action(burst=5)` grounded against visible cart controls.
  - Registered in `proofqa/explore/probes/__init__.py` and `explorer.py` across `rules_probes`, `rules_probes_goexplore`, and `full`.

### D. Independent Verifier (`proofqa/cert/verify.py`)
- Obeys Architecture Rule 3: strictly isolated without imports from `explore`, `oracles`, or `llm`.
- Inspects `claim.json`: if `tier == "INTERMITTENT"`, executes 5 replays with concurrent burst support.
- If target signature reproduces $\ge 2$ of $5$ times, returns `VerifyVerdictKind.VALID_INTERMITTENT`.
- If reproduced $< 2$ times, returns `INVALID`.

### E. Trace Shrinking (ddmin for INTERMITTENT)
- In `proofqa/proof/shrink.py`:
  - Evaluator uses $m$-of-$n$ ($2$-of-$5$) threshold for traces containing burst actions.
  - Minimizes burst size: systematically tests reduced burst counts ($b \in [2, burst)$) to retain the smallest burst size triggering the failure.

---

## 4. Empirical Verification & Negative Control

1. **Reproduction & Verification**:
   - `test_burst_action_b09_intermittent_repro_and_verify`: Triggered B09, generated certificate with `Tier.INTERMITTENT` and `observed_rate="4/5"`, independently verified as `VALID_INTERMITTENT`.
2. **Negative Control (30 runs with B09 disabled)**:
   - `test_b09_negative_control_30_runs`: Ran the exact burst trace 30 times against pristine Shop Twin with B09 disabled.
   - **Result**: Exactly **0** signature hits, 30/30 clean passes (0.0% false positive rate).
3. **Decoy D10 Isolation**:
   - `test_b09_burst_against_decoy_d10`: Ran burst trace against Decoy D10 (rapid hits return friendly HTTP 429).
   - **Result**: D10 returned HTTP 429, never HTTP 500. Exactly **0** false positive findings.
