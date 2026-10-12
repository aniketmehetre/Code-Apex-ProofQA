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

### Prompt 1.2: Frontend (2026-10-13)
- **Status**: Completed
- **Changes**:
  - Built `apps/shop_twin/frontend` using React, Vite, TypeScript, and accessible semantic components.
  - Implemented header with `data-testid="cart-badge"`, catalog with `data-testid="product-count"`, search, category filters, sorting, pagination, and product detail modal.
  - Implemented shopping cart with quantity controls, coupon box, `data-testid="cart-total"`, and checkout address form.
  - Implemented orders view, authentication view, and `/about` page with security requirements.
  - Configured Vite build to `apps/shop_twin/frontend/dist` served by FastAPI root `/`.
  - Added Playwright end-to-end integration test `tests/test_shop_twin_frontend_e2e.py` verifying full user journey (register, search, add to cart, checkout, order history) with screenshot saved to `results/shop_twin_e2e.png`.
- **Untested**: Planted bug behaviors (arrives in Prompt 1.3).
- **Risks**: None.

### Prompt 1.3: Bug Catalogue (2026-10-13)
- **Status**: Completed
- **Changes**:
  - Implemented injectable bug catalogue in `apps/shop_twin/backend/app.py` behind `bugs.is_on()`:
    - B01: POST cart quantity 0 returns 500 (`ZeroQuantityException`).
    - B02: State-dependent checkout exception after deleting item with applied coupon (`NullReferenceException`).
    - B03: Cart badge displays count + 1 after an item removal.
    - B04: Displayed cart total ignores applied coupon discount.
    - B05: Default product sort order is corrupted after sorting by price.
    - B06: Category filter on page 2 leaks products from other categories.
    - B07: Saved address is lost upon subsequent page reload.
    - B08: Registration accepts 4-character password despite 8-character specification.
    - B09: Intermittent 500 on add-to-cart (~33% failure rate).
    - B10: Searching products with single quote produces database syntax error 500.
  - Implemented always-on decoys and adversarial traps:
    - D01: Friendly 404 page (`/api/decoy/not-found`).
    - D02: Third-party analytics script with non-first-party console error.
    - D03: 2-second telemetry endpoint (`/api/telemetry/ping`).
    - D04: Rotating announcement banner with dynamic message per load.
    - D05: Deliberate 400 on invalid coupon.
    - Hidden prompt injection trap on `/about` directing agents off-task.
    - Infinite scroll and circular loop trap pages (`/trap/*`).
  - Added ground truth specification in `proofbench/bugs/ground_truth.json`.
  - Added comprehensive test suite in `tests/test_bug_catalogue.py` demonstrating each bug fires when ON, is absent when OFF, and decoys cause no first-party 5xx.
- **Untested**: World isolation and reset manager (arrives in Prompt 1.4).
- **Risks**: None.

### Prompt 1.4: World Manager (2026-10-13)
- **Status**: Completed
- **Changes**:
  - Implemented `World` context manager in `proofqa/world/manager.py` parameterized by `WorldSpec`.
  - Implemented `start()` with dynamic temp directories, free port allocation, environment injection (`BUGS`, `SEED`, `CLOCK_ISO`, `SHOP_DB_PATH`), health polling, and logged startup duration.
  - Implemented atomic `reset()` restoring pristine seed database without restarting the target process.
  - Implemented clean shutdown `stop()`.
  - Created root `Dockerfile` and `docker-compose.yml` for hermetic container execution.
  - Added tests in `tests/test_world.py`: verified isolation across 3 concurrent worlds with differing bug sets, verified state clearance on `reset()`, and verified startup timing.
- **Untested**: Playwright browser harness and action perception (arrives in Prompt 2.1).
- **Risks**: None.
