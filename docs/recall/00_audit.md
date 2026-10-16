# ProofQA 2.0: Recall Audit (Prompt 0)
> **Branch**: `recall-v2`  
> **Date**: 17 Oct 2026  
> **Baseline Benchmark Summary**: `results/recall/00_baseline.json` (Recall: 10.0%, Precision: 100.0%)

---

## 1. Code Architecture Mapping

| Component | Implementation File & Primary Symbol | One-Line Description |
|---|---|---|
| **Explorer** | `proofqa/explore/explorer.py:RuleBasedExplorer` | Directed state-graph frontier explorer using ARIA/URL fingerprints, loop/trap pruning, and clean-world replay backtracking. |
| **Proposer** | `proofqa/llm/proposer.py:Proposer` | DOM-grounded candidate action selector filtering ungrounded proposals with prompt-injection defense and offline heuristic fallback. |
| **Oracle Class A** | `proofqa/oracles/hard_signals.py:HardSignalsOracle` | Event-hook oracle detecting first-party uncaught HTTP 5xx responses, unhandled JavaScript runtime errors, and fatal console logs. |
| **Oracle Class B** | `proofqa/oracles/relations/runner.py:RelationsRunner` | Evaluates metamorphic relational invariants (sort order reversibility, category filter subset isolation, account address reload persistence). |
| **Oracle Class C** | `proofqa/oracles/spec_claims.py:SpecClaimsOracle` | Regex/phrase extraction of stated specification policies (e.g. password minimum length) and verification against backend responses. |
| **Oracle Class D** | `proofqa/oracles/cross_layer.py:CrossLayerOracle` | Compares rendered UI DOM facts (badge counts, calculated totals) with intercepted first-party API JSON payload properties. |
| **Oracle Class E** | `proofqa/oracles/temporal_diff.py:TemporalDifferentialOracle` | Evaluates identical action traces across two builds to flag behavioral regressions without human ground truth. |
| **Noise Filter** | `proofqa/tape/recorder.py:NoiseProfile` | Whitelists first-party origins and filters out third-party telemetry, ad beacons, and benign browser console warnings. |
| **Replay Engine** | `proofqa/proof/replay.py:replay` | Three-valued execution engine (`FAIL`, `PASS`, `UNRESOLVED`) verifying failure reproduction on fresh ephemeral World instances. |
| **ddmin** | `proofqa/proof/shrink.py:shrink_trace` | Multi-level delta debugging (state-drop, binary complement reduction, value minimization) strictly locking the target failure signature. |
| **Certificate Builder** | `proofqa/cert/builder.py:build_certificate` | Packages confirmed minimal traces, failure signatures, and environmental descriptors into hermetic SHA-256 sealed bundles. |
| **Verify Binary** | `proofqa/cert/verify.py:verify_certificate` | Rule 3 independent zero-knowledge verifier enforcing manifest integrity and isolated Playwright reproduction without pipeline imports. |
| **Bench Adjudicator** | `proofbench/adjudicate.py:Adjudicator` | Matches emitted findings against `ground_truth.json` specifications, identifying true bugs, decoys, duplicates, and false positives. |
| **Validate-Menu** | `demo/validate_menu.py:validate_flag` | Interactive harness demonstrating judge's-choice catalogue bugs end-to-end through pipeline, certification, verification, and adjudication. |

---

## 2. Dev Split Definition & Root Cause of 10% Recall

### Dev Split Specification
- **Planted Ground Truth Bugs**: 10 bugs (`B01` through `B10` in `proofbench/bugs/ground_truth.json`).
- **Dev Split Bugs Evaluated in Bench**: `dev_bugs = ["B01", "B03", "B05", "B10"]` in `proofbench/runner.py`.
- **Seeds Evaluated**: `seeds = [42, 43, 44, 45, 46]` (5 distinct seeds).
- **Adjudication Calculation**:
  $$\text{Recall} = \frac{\text{True Bugs Found}}{\text{Total Ground Truth}} = \frac{1}{10} = 0.10 \quad (10.0\%)$$
  95% Wilson Score Confidence Interval: $[0.0179, 0.4042]$.

### Root Cause of 10% Recall
1. **Benchmark Runner Bypassed Autonomous Exploration**: In `proofbench/runner.py` (lines 68-83), `BenchmarkRunner.run()` instantiated a single hardcoded finding for `B01` (`cand_b01` with `quantity=0`) and passed `initial_candidates=[initial_cand]` to `pipeline.run()`.
2. **Explorer Never Executed**: In `proofqa/pipeline.py` (line 98), `if not initial_candidates:` guards the call to `await explorer.explore()`. Passing `initial_candidates` completely skipped autonomous exploration.
3. **Only One Bug Adjudicated**: Across all 5 seeds, only `B01` was ever replayed, certified, and adjudicated. Because `total_ground_truth = 10`, recall was statically locked at exactly $1 / 10 = 10\%$.
4. **General Explorer Inability to Reach Other Bugs**: Even when `explorer.explore()` is run autonomously, the current rule-based explorer lacks:
   - Boundary value generation (zero, negative, huge numbers, quotes) based on field semantics.
   - Token pool extraction to harvest promo codes (like `SAVE10`) from DOM text or placeholders.
   - Deep state navigation required for stateful sequences (B02: add 2 items $\to$ apply coupon $\to$ delete item $\to$ checkout).
   - Autonomous execution of metamorphic reversions (B05 sort restoration, B07 address persistence).
   - Hooking Class B, C, and D oracles to passive explorer tape events.

---

## 3. Validate-Menu Audit (All Ten Bugs B01..B10)

Execution of `.\make.bat validate-menu all`:

| Bug ID | Present in `MENU_FLAGS`? | Verdict | Pre-Shrink Steps | Post-Shrink Steps | Cause of Error / Status |
|---|---|---|---|---|---|
| **B01** | Yes | **PASS (VALID)** | 4 | 4 | Injected `quantity="0"` triggers HTTP 500 `ZeroQuantityException`. Manifest verified, replayed 1/1, adjudicated `true_bug`. |
| **B02** | Yes | **FAIL** | 4 | N/A | Scripted steps in `MENU_FLAGS` lacked coupon code application (`SAVE10`) and secondary item addition required to trigger B02. |
| **B03** | Yes | **FAIL** | 4 | N/A | `FailureSignature.kind="cross_layer_inconsistency"`, but `signature_from_events()` in `tape.py` only extracts `http_5xx` and `page_error`. Replay observes no failure. |
| **B04** | **No (Skipped)** | **SKIPPED** | N/A | N/A | Not registered in `MENU_FLAGS`. |
| **B05** | Yes | **FAIL** | 3 | N/A | `FailureSignature.kind="relation_violation"`, which is not an HTTP 5xx or unhandled JS exception; replay reports `PASS` (no crash observed). |
| **B06** | **No (Skipped)** | **SKIPPED** | N/A | N/A | Not registered in `MENU_FLAGS`. |
| **B07** | Yes | **FAIL** | 3 | N/A | `FailureSignature.kind="relation_violation"`. Replay does not evaluate Class B persistence relation; reports `PASS` (no crash observed). |
| **B08** | **No (Skipped)** | **SKIPPED** | N/A | N/A | Not registered in `MENU_FLAGS`. |
| **B09** | **No (Skipped)** | **SKIPPED** | N/A | N/A | Not registered in `MENU_FLAGS`. |
| **B10** | Yes | **FAIL** | 2 | N/A | Step filled search input with `'` but never pressed Enter or clicked the Submit Search button; request never dispatched to `/api/products`. |

---

## 4. Current Explorer Telemetry on Clean Autonomous Walk

When `RuleBasedExplorer` runs without hints (`budget_steps=25`):
- **Pages Visited**: Only `/` and `/about`. Modal opened on product clicks.
- **Controls Clicked**: Top navigation links, product card headings, modal close button.
- **Forms Filled**: Search box filled with default rotating strings from `inputs.py` (`"headphones"`, `"keyboard"`). Never submitted because search input is not followed by Enter key press.
- **Register / Login**: Never occurred. Explorer never navigated to `/account` or opened sign-in modal.
- **Cart Size**: Maximum cart size reached was 1 (standard item addition).
- **Promo Field**: Never filled (cart view with coupon form was never visited).

---

## 5. Shop Twin Bug Catalogue Deep Dive (B01–B10)

| Bug ID | Exact Trigger Condition in Backend | Seed Randomness? | Client-Side Form Validation Blocker? | Login Required? | Where Required Inputs Appear in UI / App |
|---|---|---|---|---|---|
| **B01** | `POST /api/cart` with `quantity == 0` | Deterministic | No. Modal input has `min="0"`, which permits `0`. (Client allows submit). | No | Quantity input in Product Modal (`id="modal-qty-input"`). |
| **B02** | `POST /api/checkout` when `sess.applied_coupon` is truthy and `sess.removed_item` is True | Deterministic | No. | No (anonymous cart supported) | Promo code `SAVE10` appears in hero banner and placeholder `placeholder="Coupon (e.g. SAVE10)"`. |
| **B03** | `GET /api/cart` returns `badge_count = item_count + 1` after an item was deleted | Deterministic | No. | No | Badge element in header `[data-testid="cart-badge"]`. |
| **B04** | `GET /api/cart` returns `total = subtotal` ignoring discount when coupon applied | Deterministic | No. | No | Cart summary total element `[data-testid="cart-total"]`. |
| **B05** | `GET /api/products` order reverts to price sort when default sort requested after sorting by price | Deterministic | No. | No | Sort dropdown select control (`aria-label="Sort products by"`). |
| **B06** | `GET /api/products?category=...&page=2` returns products from other categories | Deterministic | No. | No | Category filter buttons and pagination buttons. |
| **B07** | `GET /api/account/address` returns `{"address": None}` after address was saved | Deterministic | No. | **Yes** (requires authenticated session) | Address textarea and Save button on `/account` page. |
| **B08** | `POST /api/register` with `len(password) == 4` returns HTTP 200 instead of 400 | Deterministic | No. Registration password input has no `minlength` attribute in DOM. | No (registration endpoint) | Policy copy on `/about` and above form: *"passwords must be at least 8 characters in length"*. |
| **B09** | `POST /api/cart` raises HTTP 500 when `random.random() < 0.34` | **Stochastic** (uses unseeded Python `random.random()`, ~34% rate) | No. | No | Product cards and modal Add to Cart buttons. |
| **B10** | `GET /api/products?q=...` raises HTTP 500 when `'` is present in query param `q` | Deterministic | No. Search input has no regex restriction. | No | Search input field (`aria-label="Search products"`). |

---

## 6. Action Contract & Browser Harness Capability Audit

### Capabilities Present
- `ActionKind.FILL`: Fully supported via Playwright `page.fill()`.
- `ActionKind.CLICK`: Fully supported via Playwright `page.click()`.
- `ActionKind.SELECT`: Fully supported via Playwright `page.select_option()`.
- `ActionKind.PRESS`: Supported via Playwright `page.press()`.
- `ActionKind.WAIT`: Supported via Playwright `page.wait_for_timeout()`.
- `ActionKind.GOTO`: Supported for absolute and relative paths via `page.goto()`.

### Missing Gaps / Capabilities Needed for Full Recall
1. **Reload Primitive**: Currently reloads require a `GOTO` to the current URL. A dedicated `ReloadProbe` or `page.reload()` wrapper is needed.
2. **Concurrent Burst Actions**: For `B09` (concurrency lock timeout), executing actions sequentially at 300ms intervals cannot simulate concurrent thread contention.
3. **Form Submission Association**: Typing in a search or promo box without pressing `"Enter"` or finding the sibling submit button fails to dispatch the request.

---

## 7. Duplicate Findings & Clustering Audit
- **Current Finding Deduplication**: `proofqa/pipeline.py` deduplicates findings within a single run using a hash of `kind + first_party_endpoint + message_norm`.
- **Adjudicator Handling**: `proofbench/adjudicate.py` marks repeated hits on the same planted bug as `"duplicate"`. Precision and recall remain unpolluted.
- **Gap**: There is currently no persistent finding clustering that groups multiple similar failure signatures under a single unified defect report with an occurrence counter.

---

## 8. Tape Recording & Relational Evidence Audit
- **Request Bodies**: `proofqa/tape/recorder.py` stores only `NetworkEvent.request_body_hash = sha256(post_data)`. The raw body string is currently not persisted in `NetworkEvent`.
- **UiFact Types**: `UiFactEvent(label, ui_value, api_value, api_ref, timestamp_ms)` exists in contracts, but is populated only by the `CrossLayerOracle`, not during general tape recording.
- **Relational Invariant Evidence**: Class B (persistence) and Class C (spec claims) currently operate via standalone evaluate scripts rather than listening to passive tape events.

---

## 9. Blindness & Isolation Audit
- **AST Inspection**: `proofqa/explore/` contains zero imports of `ground_truth`, `proofbench`, or `apps/shop_twin/backend/bugs.py`.
- **Runtime Leak Risk**: `explorer` currently accepts `World`, which contains `world.world_spec.bugs`. While `explorer.py` does not currently read `world.world_spec.bugs`, an agent could theoretically access it.
- **Remediation Required**: Prompt 2 must introduce a stripped-WorldSpec test and enforce that `proofqa/explore` is passed a `WorldSpec` with `bugs=[]` or is provably blind to active flags.

---

## 10. Capability & Strategy Map

| Bug ID | Trigger Condition | Reach Needs | Blocker Today | Oracle Exists? | Proposed Capability (Prompt #) |
|---|---|---|---|---|---|
| **B01** | `POST /api/cart` with qty 0 | Boundary value 0 in quantity input | Explorer enters random numbers, doesn't target boundary 0 | Yes (Class A) | BoundaryProbe (Prompt 4) |
| **B02** | Add 2 items $\to$ Apply `SAVE10` $\to$ Remove 1 $\to$ Checkout | Deep state sequence with promo code | Explorer lacks stateful memory and coupon token | Yes (Class A) | TokenPool + Go-Explore (Prompts 4, 6) |
| **B03** | Add item $\to$ Remove item $\to$ inspect badge count | Add then remove sequence | Explorer does not systematically exercise inverse pairs | Yes (Class D) | InversePairProbe + Class D every step (Prompt 5) |
| **B04** | Add item $\to$ Apply promo $\to$ inspect total | Promo code applied in cart | Explorer never enters promo code in cart | Yes (Class D) | TokenPool + Class D every step (Prompts 4, 5) |
| **B05** | Select sort $\to$ revert sort $\to$ check product order | Select and revert dropdown | Explorer does not systematically revert selections | Yes (Class B) | RevertProbe (Prompt 5) |
| **B06** | Pagination page 2 $\to$ category filter | Page 2 + category filter | Explorer does not combine multi-control states | Yes (Class B) | PairwiseProbe (Prompt 5) |
| **B07** | Login $\to$ save address $\to$ reload page | Auth bootstrap + address fill + reload | Explorer never logs in or reloads after PUT | Yes (Class B) | AuthBootstrap + ReloadProbe (Prompts 4, 5) |
| **B08** | Register with 4-char password | 4-char password on registration | Explorer fills valid 12-char passwords | Yes (Class C) | SpecFacts + BoundaryProbe (Prompt 4) |
| **B09** | Rapid concurrent add to cart | Concurrent thread contention | Explorer actions are strictly serial with delays | Yes (Class A) | BurstProbe + INTERMITTENT tier (Prompt 8) |
| **B10** | Single quote in search box + submit | Submit `'` in search form | Explorer does not submit search form with quote | Yes (Class A) | FormPlan + BoundaryProbe (Prompt 4) |

---

## 11. Contract Changes Needed?

### Decision: **NO Breaking Changes Required**
- `contracts.py` is **FROZEN** (Rule 8).
- All core contracts (`Action`, `Locator`, `Finding`, `CertificateManifest`, `VerifyVerdict`) support the required abstractions.
- For Prompt 8 (intermittent bugs), if an optional `burst: int = 1` field is added to `Action`, it will be strictly **additive and optional** (defaulting to 1), preserving 100% backward compatibility with all existing certificates and schemas. Zero breaking contract changes will be made.
