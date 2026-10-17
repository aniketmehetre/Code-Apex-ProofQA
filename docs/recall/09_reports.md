# ProofQA 2.0: Prompt 9 — Finding Clustering and Report Output

**Date:** 17 Oct 2026  
**Branch:** `recall-v2`  
**Status:** Completed  

---

## 1. Goal and Overview

As explorer capabilities and recall increase, identical failure signatures can be triggered repeatedly from different exploration paths. To ensure system output remains clean, high-precision, and actionable without mutating the frozen certificate schema:
1. **Finding Clustering**: Groups findings by deterministic signature key, retains the minimal reproduction trace, and records occurrence counts.
2. **Human-Readable Certificate Reports**: Standalone Markdown reports (`report.md`) generated strictly outside the sealed certificate directory.
3. **Exploration Run Reports**: Structured `run_report.md` and `run_report.json` capturing coverage, unique findings, suppressed noise, and unresolved counts.
4. **Dashboard & CLI Exposure**: Integrated `proofqa report <cert>` CLI and REST endpoints.

---

## 2. Architecture & Implementation

### A. Signature-Based Finding Clustering (`proofqa/cert/cluster.py`)
- **Deterministic Cluster Key**:
  $$\text{Key} = \text{oracle\_class} : \text{sig.kind} : \text{first\_party\_endpoint} : \text{status} : \text{error\_type} : \text{message\_norm}$$
- **Minimal Trace Selection**: When duplicate findings match the same cluster key, the cluster retains the finding with the fewest action steps (with confidence as tie-breaker) and increments the `occurrences` counter.
- **Precision/Recall Integrity**: Duplicate finds do not inflate precision or recall metrics in adjudication.

### B. Certificate Report Engine (`proofqa/cert/report.py`)
- **Isolation**: Derived **only** from sealed certificate artifacts (`claim.json`, `repro.json`, `signature.json`, `replay.json`, `manifest.json`). No LLM calls.
- **Plain English Action Translation**:
  - `ActionKind.GOTO` $\rightarrow$ `Navigate to URL: '<url>'`
  - `ActionKind.CLICK` $\rightarrow$ `Click <role> "<name>"` (with burst annotations when `burst > 1`)
  - `ActionKind.FILL` $\rightarrow$ `Fill <input> with "<val>"`
  - `ActionKind.SELECT` $\rightarrow$ `Select option "<val>" in <select>`
- **Expected vs Observed Templates**: Per-class deterministic templates for Classes A through F.
- **Verification Command**: Direct invocation instructions (`proofqa verify "<cert_path>"`).
- **Placement**: Written **outside** the certificate folder (e.g. `<cert>_report.md`), preserving cryptographic manifest integrity.

### C. Run Report Generator (`generate_run_report`)
- Emits `run_report.md` and `run_report.json` detailing:
  - Discovered unique findings count.
  - Exploration coverage: pages visited, semantic states, controls exercised, and probes fired per family.
  - Suppressed environmental noise: third-party network errors, friendly 404s, and masked layout shifts.
  - Unresolved counts: client-blocked probes and timeouts.

### D. CLI & REST API Exposure
- **CLI**: `proofqa report <cert_path> [--out <dest>]`
- **FastAPI Control Plane**:
  - `GET /certificates/{cert_id}/report` — serves report markdown or triggers attachment download.

---

## 3. Testing & Verification

- `tests/test_report.py`:
  - `test_finding_clustering_synthetic_double_find`: Proves duplicate findings for `/api/cart` are collapsed into 1 cluster with `occurrences=2` and minimal trace length of 2 steps.
  - `test_certificate_report_golden_file_step_for_step`: Validates that `demo/recorded/recorded_b01` report translates all 4 steps from `repro.json` in exact chronological sequence.
  - `test_cli_report_command`: Verifies CLI report generation outside the certificate folder.
  - `test_run_report_generation`: Verifies JSON and Markdown coverage artifact creation.
