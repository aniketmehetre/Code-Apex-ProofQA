# ProofQA 2.0: Honesty & Boundary Limits Registry

*Team VOID MAIN • Code Apex Hackathon*

In strict accordance with the ProofQA 2.0 architecture and honesty contracts, this document explicitly lists what ProofQA **proves** and what it **does not prove**.

---

## 1. What ProofQA Proves

ProofQA provides pairwise, deterministic, cryptographically sealed verification:

1. **First-Party Exception Reproduction (Class A Oracles)**
   - Proves: That a specific sequence of browser interactions reliably induces an uncaught server exception (HTTP 5xx) or unhandled browser console error at a first-party endpoint.
   - Guaranteed reproduction fidelity: Confirmed across $k$ of $k$ independent Playwright execution replays under isolated, freshly seeded world environments.

2. **Metamorphic Invariant Violations (Class B Oracles)**
   - Proves: That mathematical relations (such as sort idempotence, filter subset isolation, or account persistence round-trips) are violated under defined inputs.
   - Guarded by baseline calibration: Oracles must pass clean baselines before declaring an anomaly.

3. **Cross-Layer Inconsistency (Class D Oracles)**
   - Proves: Divergence between rendered user interface DOM representations (e.g. cart badge count, displayed subtotal) and ground-truth backend JSON payloads.

4. **Cryptographic Certificate Hermeticity**
   - Proves: That reproduction steps, failure signatures, and environmental parameters have not been tampered with since certification issuance.
   - Any single byte alteration invalidates the SHA-256 manifest check, causing `proofqa verify` to reject the certificate as `TAMPERED` before execution.

---

## 2. What ProofQA Does Not Prove

To maintain strict scientific honesty, the following limitations are explicitly bounded:

1. **Does Not Prove Global Program Correctness**
   - ProofQA proves the *presence* of certified bugs along concrete shrunk execution traces, but does not prove the absence of undiscovered bugs across unvisited state frontiers.

2. **Does Not Infer Human Intent for Non-Crash Changes**
   - For oracles in Classes B, C, and D, behavioral divergences could stem from intentional feature redesigns rather than accidental regressions.
   - ProofQA automatically tags such findings as `VERIFIED_VIOLATION` with `intent_confirmation_needed=True` and routes them to the Human Review Queue.

3. **Does Not Guarantee Third-Party Vendor Health**
   - ProofQA profiles the ambient network noise floor to mask third-party ad networks, trackers, and external CDNs, focusing strictly on first-party application endpoints.

4. **Does Not Replace Formal Mathematical Verification**
   - ProofQA is an empirical testing engine, not a formal theorem prover (such as Coq or TLA+). Replays prove counterexamples, not mathematical inductive invariances over infinite state spaces.

5. **Bounded to Specified Oracle Classes (Classes A–E)**
   - Defect detection is bounded to uncaught server/client exceptions (Class A), metamorphic relation violations (Class B), explicit specification claims (Class C), and cross-layer UI vs API network facts (Class D). Bug classes outside these categories (e.g. subtle cryptographic side-channels or zero-day memory corruption) require defining domain-specific relation oracles.

6. **E-Commerce & CRUD Lexicon Scope**
   - Exploratory state clustering and action intent mapping rely on our generic role/label lexicon (cart, checkout, address, coupon, sort, filter, pagination). Specialized applications (e.g. WebGL graphics editors or financial trading blotters) require expanding the intent lexicon.

7. **Operator Fixtures for Unguessable Tokens**
   - When a deep state transition requires a specific secret or coupon code (such as `SAVE10`) that is not present in DOM copy, placeholders, or first-party API responses, ProofQA relies on the documented operator fixtures file (`fixtures/shop.yaml`). ProofQA never embeds hard-coded dictionary cheats inside explorer code.

8. **Held-Out Sample Size ($n=5$ bugs, 10 seeds)**
   - The sealed held-out suite evaluates 5 distinct bug variants across 10 independent random seeds (50 total trials). While strictly proving that the explorer is blind to the catalogue, broader statistical generalization across arbitrary third-party codebases requires continuous expansion of the held-out suite.

---

## 3. Operational Fallback Protocol

- If network or API keys are unavailable, ProofQA operates with 100% functionality under `OFFLINE=1`.
- If live browsers are unavailable in non-GUI CI containers, pre-validated runs in `demo/recorded/` provide offline replay verification, clearly and visibly labeled as **RECORDED**.
- In the live demo, `--replay-recorded` enables zero-latency demonstration playback from `results/demo_blind_cache/events.json`.

