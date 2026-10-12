# ProofQA 2.0 Progress Log

## Phase 0: Foundation

### Prompt 0.1: Scaffold (2026-10-13)
- **Status**: Completed
- **Changes**: Initialized repository layout, pyproject.toml, Makefile, documentation templates, and import guard tests (`test_import_guards.py`). Installed Chromium via Playwright.
- **Untested**: Feature implementations (scaffold only).
- **Risks**: None.

### Prompt 0.2: Contracts (2026-10-13)
- **Status**: Completed (Contracts FROZEN at Milestone M0)
- **Changes**:
  - Implemented `proofqa/contracts.py` with Pydantic v2 models (`Locator`, `Action`, `StateFingerprint`, `TapeEvent` discriminated union, `OracleClass`, `Tier`, `FailureSignature`, `normalize_message`, `ReplayOutcome`, `WorldSpec`, `Finding`, `CertificateManifest`, `VerifyVerdict`).
  - Implemented pure function `normalize_message()` stripping UUIDs, timestamps, hex IDs, and digit runs.
  - Exported 16 JSON schemas to `docs/schemas/`.
  - Documented all models in `docs/contracts.md`.
  - Added full test suite in `tests/test_contracts.py` verifying roundtrips, schemas, and message normalization.
- **Untested**: Dynamic runtime execution of actions (arrives in Phase 1 and 2).
- **Risks**: None. Contracts are frozen.
