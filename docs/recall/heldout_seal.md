# Held-Out Evaluation Set Cryptographic Seal

**Tag:** `heldout-v1`  
**Commit Hash:** `700a185fb9acba5e30fc5712dc8bbf9434a60c6e`  
**Ground Truth Path:** `proofqa/bench/ground_truth_heldout.json`  
**SHA-256 Checksum:** `66964f57165b34835a1c8b9a42d2d22892ff95f270eb27061b1704c0c4fa7364`  
**Sealed At:** 2026-10-17  

---

## 1. Held-Out Integrity Guarantee

This document certifies that the held-out bug suite (`H01`–`H05`) and the extended decoys (`D06`–`D10`) were specified, implemented in `proofqa/world/heldout.py`, and cryptographically sealed **prior** to any explorer enhancements, probe registry implementations, or oracle tuning.

### Strict Non-Tuning Guarantees
1. **Zero Prior Exposure**: Neither `RuleBasedExplorer` nor any probe module has been executed on the held-out catalogue.
2. **Deterministic Scripted Proof**: All 5 held-out bugs and 5 decoys are verified exclusively via deterministic HTTP requests in `tests/test_heldout.py`.
3. **AST Blindness Guard**: Enforced by `tests/test_import_guards.py::test_blindness_guard_ast`, proving that `proofqa/explore`, `proofqa/llm`, and `proofqa/spec` cannot import `proofqa.world.heldout`, `apps.shop_twin.backend.bugs`, `proofbench`, or ground truth files.
4. **Seed Separation**: Held-out evaluation is strictly confined to Seeds 101–110. Development tuning occurs exclusively on Seeds 1–10.

---

## 2. Held-Out Bug Catalogue (`H01`–`H05`)

| Bug ID | Class | Category | Minimal Trigger Description | Expected Failure Signature |
|---|---|---|---|---|
| **H01** | A | Crash | `POST /api/cart` with negative quantity | `http_5xx` 500 on `/api/cart` (`NegativeQuantityException`) |
| **H02** | A | Crash Injection | `GET /api/products` with `"`, `%`, or `\` in query `q` | `http_5xx` 500 on `/api/products` (`DatabaseError`) |
| **H03** | B | Metamorphic Sort | Sort products by name, then revert to default sort | `relation_violation` on `/api/products` (`MetamorphicViolation`) |
| **H04** | B | Persistence | `PUT /api/account/profile` with `display_name`, then `GET` | `relation_violation` on `/api/account/profile` (`MetamorphicViolation`) |
| **H05** | A | Stateful Crash | Direct checkout under coupon without line item removal | `http_5xx` 500 on `/api/checkout` (`NullReferenceException`) |

---

## 3. Extended Decoys (`D06`–`D10`)

| Decoy ID | Target Subsystem | Documented Intended Behavior | Expected Outcome |
|---|---|---|---|
| **D06** | Product Catalog Sort | Equal-price items legitimately tie-break in reverse order | No relation violation; benign reordering |
| **D07** | Account Preferences | `/api/preferences` returns device-local preferences only | Benign response with explicit notice |
| **D08** | Cart Validation | Out-of-bounds quantity returns friendly HTTP 400 | HTTP 400 Client Error (never HTTP 5xx) |
| **D09** | Product Navigation | Page and filter reset on reload by design | Intended navigation reset |
| **D10** | Rate Limiting | Rapid bursts return friendly HTTP 429 | Friendly HTTP 429 (never HTTP 5xx) |
