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

## Phase 1: The shop twin (Track A)

### Prompt 1.1: Backend (2026-10-13)
- **Status**: Completed
- **Changes**:
  - Built `apps/shop_twin/backend/app.py` with FastAPI and SQLite/SQLModel models.
  - Implemented endpoints under `/api`: `register`, `login`, `logout` (cookie session), `GET /products` (with `q`, `category`, `sort`, `page`, `page_size`, `total`), cart CRUD (`GET`, `POST`, `PATCH`, `DELETE`), `POST /coupons/apply`, `POST /checkout`, `GET`/`PUT /account/address`, `GET /orders`, and `GET /health`.
  - Created `apps/shop_twin/backend/seed.py` generating deterministic `seed.db` with 60 products across 4 categories and 3 coupons.
  - Added `apps/shop_twin/backend/bugs.py` exposing `is_on(id)` reading `BUGS` environment variable.
  - Added launcher in `apps/shop_twin/backend/main.py` creating fresh runtime copy of `seed.db` and binding to a free port.
  - Added integration test suite in `tests/test_shop_twin_backend.py` exercising every endpoint with HTTPX.
- **Untested**: Frontend UI integration (arrives in Prompt 1.2).
- **Risks**: None.
