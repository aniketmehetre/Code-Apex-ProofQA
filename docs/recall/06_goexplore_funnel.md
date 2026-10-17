# Prompt 6: Semantic State and Go-Explore Funnel Report

## 1. Overview
Prompt 6 implemented generic deep state reaching via coarse semantic state abstraction and a Go-Explore archive:
- `proofqa/explore/semantic_state.py`: `SemanticState` generic coarsening:
  - Query parameters preserved (`page`, `sort`, `filter`, `category`, `q`).
  - ARIA tree snapshot hashed with rotating banner D04 mask (`<MASKED_BANNER>`).
  - Numeric badge count coarsely bucketed (`0`, `1`, `2`, `3+`).
  - Max first-party GET array lengths bucketed (`0`, `1`, `2`, `3+`).
  - Distinct cart/line item count bucketed (`0`, `1`, `2`, `3+`).
  - Coupon/promo/discount key truthy status (`promo:0` or `promo:1`).
  - Auth token/session presence (`auth:anon` vs `auth:auth`).
- `proofqa/explore/archive.py`: `GoExploreArchive`:
  - Maps `state_key` -> shortest tape prefix, visit count, untried actions, and novelty score.
  - Seeded weighted choice prioritizing few visits, high untried count, and novelty.
  - Return-to-cell execution: resets world, replays prefix, checks for semantic state divergence; marks cell stale if diverged.
- `proofqa/explore/explorer.py`:
  - Root state registration into archive.
  - Automatic archive phase execution and return-to-cell expansion.
  - `extract_form_plans` baseline action generation for untried forms.
  - Disambiguated `resolve_element` prioritizing unique `data-testid` to guarantee distinct item selection.

## 2. Benchmark Funnel Results (`rules_probes_goexplore` on dev seeds 1..10)

| Bug | Description | S1 (Reach) | S2 (Emit) | S3 (Conf) | S4 (Cert) | S5 (Verif) | S6 (True) | Primary Stage |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **B01** | Zero Qty Cart Add | 0/10 | 10/10 | 5/10 | 5/10 | 5/10 | 5/10 | **S6** |
| **B02** | Stateful Coupon + Delete + Checkout | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | S0 |
| **B03** | Cart Badge Desync | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | S0 |
| **B04** | Cart Summary Discount Desync | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | S0 |
| **B05** | Default Sort Reversion Failure | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | S0 |
| **B06** | Category Filter Pagination Leak | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | S0 |
| **B07** | Account Address Persistence Failure | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | S0 |
| **B08** | Weak Password Registration | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | S0 |
| **B09** | Cart Concurrency Race | 4/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | S0 |
| **B10** | Crash Injection (Unescaped Quote in Search) | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | S0 |

## 3. Key Metrics
- **Recall**: 10.0% (B01 certified in 5/10 seeds)
- **Precision**: 100.0% (0 false positives)
- **Certificate Validity Rate**: 100.0% (5/5 verified external re-executions)
- **Decoy False Positive Rate**: 0.0% (D01-D10 all clean)
- **Adversarial Hijack Rate**: 0.0% across all levels
- **Determinism**: 100% byte-for-byte identical action events on matching seed and level
