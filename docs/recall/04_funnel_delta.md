# Prompt 4: Funnel Delta and Generic Input Discovery Report

## 1. Overview
Prompt 4 implemented generic input discovery without bug-specific knowledge:
- `proofqa/spec/facts.py`: Deterministic regex extraction of specification facts (`SpecFactStore`) from DOM attributes and page copy.
- `proofqa/explore/forms.py`: `FormPlan` abstractions deriving valid baselines and boundary values per input type.
- `proofqa/explore/probes/boundary.py`: `BoundaryProbe` evaluating edge cases (min-1, min, min+1, max, max+1, 0, -1, quotes, unicode).
- `proofqa/explore/tokens.py`: `TokenPool` harvesting coupons/promo tokens from DOM text and placeholders.
- `fixtures/shop.yaml`: Documented operator fixtures for hermetic test execution.
- `proofqa/explore/auth.py`: `AuthBootstrap` handling authentication walls with valid baseline credentials.
- `proofqa/oracles/spec_claims.py`: Extended Class C oracle evaluating transitions against `SpecFactStore` requiring condition (c) 2xx write response.

## 2. Benchmark Funnel Results (`rules_probes` on dev seeds 1..10)

| Bug | Description | S1 (Reach) | S2 (Emit) | S3 (Conf) | S4 (Cert) | S5 (Verif) | S6 (True) | Primary Stage |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **B01** | Zero Qty Cart Add | 0/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | **S6** |
| **B02** | Stateful Coupon + Delete + Checkout | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | S0 |
| **B03** | Cart Badge Desync | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | S0 |
| **B04** | Cart Summary Discount Desync | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | S0 |
| **B05** | Default Sort Reversion Failure | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | S0 |
| **B06** | Category Filter Pagination Leak | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | S0 |
| **B07** | Account Address Persistence Failure | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | S0 |
| **B08** | Weak Password Registration | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | S0 |
| **B09** | Cart Concurrency Race | 10/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | **S1** |
| **B10** | Unescaped Quote in Search | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | S0 |

## 3. Key Metrics
- **Recall**: 10.0% (found in 100% of tested seeds)
- **Precision**: 100.0% (0 false positives)
- **Certificate Validity Rate**: 100.0% (10/10 verified external re-executions)
- **Decoy False Positive Rate**: 0.0% (D01-D10 all clean, D08 returns friendly 400 without false flag)
- **Adversarial Hijack Rate**: 0.0% across all levels
