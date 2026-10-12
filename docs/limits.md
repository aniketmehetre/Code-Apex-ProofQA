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

---

## 3. Operational Fallback Protocol

- If network or API keys are unavailable, ProofQA operates with 100% functionality under `OFFLINE=1`.
- If live browsers are unavailable in non-GUI CI containers, pre-validated runs in `demo/recorded/` provide offline replay verification, clearly and visibly labeled as **RECORDED**.
