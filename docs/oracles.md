# ProofQA Oracles Reference & Grounded Specifications

This document defines the mathematical models, heuristic boundaries, and honest limitations of ProofQA's verification oracles across classes A through E.

---

## 1. Oracle Hierarchy Overview

ProofQA organizes all verification oracles into grounded proof tiers:
- **Class A (Hard Signals):** Unambiguous execution faults: first-party HTTP 5xx responses, unhandled JavaScript runtime exceptions (`PageErrorEvent`), and console error events.
- **Class B (Metamorphic Relations):** Structural behavioral invariants (sort monotonicity, filter subsets, search narrowing, round-trip reversibility).
- **Class C (Spec Claims):** Verifiable constraints extracted directly from human specification text with quote spans.
- **Class D (Cross-Layer Consistency):** Semantic comparison between raw network API responses and visual DOM/ARIA rendering facts.
- **Class E (Temporal Differential):** Replay execution comparisons across different software builds.

---

## 2. Class A: Hard Signals (`proofqa/oracles/hard_signals.py`)

### Heuristic Rules
1. **First-Party Isolation:** Network requests must share the primary origin scheme and host with the target world (`world_origin`). Third-party requests (e.g. Decoy D02 telemetry tracker `https://analytics.external-telemetry-thirdparty.invalid`) are strictly excluded.
2. **Noise Floor Profiling:** Pre-existing console or network warnings discovered during dual-pass baseline exploration (`NoiseProfile`) are excluded from generating findings.
3. **Normalization:** Exception messages and network endpoints are sanitized via `normalize_message()` to strip variable timestamps, UUIDs, memory addresses, and digit runs before signature generation.

### Known Limits
- Class A does not catch logic errors where the backend returns HTTP 200 with wrong or corrupted payload.
- Server-side timeouts that manifest as delayed 200 responses are outside Class A's scope.

---

## 3. Class D: Cross-Layer Consistency (`proofqa/oracles/cross_layer.py`)

### Heuristic Rules
1. **Fact Extraction:**
   - **Cart Badge:** Extracts numeric item count from `[data-testid="cart-badge"]`.
   - **Rendered Product Count:** Extracts catalog size from `[data-testid="product-count"]`.
   - **Cart Total:** Extracts currency floating point value from `[data-testid="cart-total"]`.
2. **Generic Matcher:**
   - Integer counts compared with exact equality (tolerance = 0).
   - Currency totals compared with standard cent tolerance ($\epsilon = 0.01$).
3. **Settle Delay Filter:**
   - Any apparent mismatch triggers a mandatory `settle_delay_seconds` (0.5s) re-check to rule out transient CSS transition or optimistic UI latency before issuing a candidate finding.

### Detected Bugs
- **B03 (Cart Badge Mismatch):** UI badge shows count + 1 after item removal.
- **B04 (Cart Total Ignores Discount):** Rendered total ignores applied coupon discount while API total reflects it.

### Known Limits
- Asynchronous polling backends may experience temporary consistency lag exceeding the settle delay.
- Non-standard currency formats or localization schemes require explicit regex matchers.

---

## 4. Class B: Metamorphic Relations (`proofqa/oracles/relations`)

### Relations Defined
1. **Sort Monotonicity:** Sorting by Price Ascending must satisfy $P_{i} \le P_{i+1}$ for all items.
2. **Sort Restoration:** Sorting and returning to default order must restore the initial permutation.
3. **Filter Subset:** Filtering by Category must yield a strict subset of items matching that category.
4. **Search Narrowing:** A more specific search query must yield a subset of a broader search query.
5. **Round-Trip Reversibility:** Adding an item and deleting it returns cart to initial state.
6. **State Persistence:** Saving an address and reloading the page preserves the identical address.

### Validation Gate
Every relation must pass `validate()` across 3 runs on a clean world. If a relation fails validation on a clean baseline, it is rejected to eliminate false positives.

### Known Limits
- Metamorphic testing requires predictable catalog states; dynamic collaborative multi-user mutations can violate monotonicity legitimately.
