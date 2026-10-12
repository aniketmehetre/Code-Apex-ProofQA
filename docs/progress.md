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

## Phase 2: Harness, tape, replay (Track B)

### Prompt 2.1: Harness and Perception (2026-10-13)
- **Status**: Completed
- **Changes**:
  - Implemented `BrowserHarness` in `proofqa/browser/harness.py`: async Playwright harness configuring fixed viewport (1280x720), frozen system Date via page init script, and Mulberry32 seeded PRNG replacing `Math.random()`.
  - Implemented perception layer in `proofqa/browser/perception.py`: ARIA tree extraction, simhashing (64-bit FNV-1a based), stable action IDs hashing role, accessible name and ancestry, volatile region detection & masking for dynamic banners (e.g. Decoy D04), and same-origin safety filtering with destructive action deny-lists.
  - Implemented prioritized action executor in `proofqa/browser/executor.py` evaluating locators in order: `role` + `name`, `label`, `testid`, with CSS fallback, returning structured outcome (`ok` or `not_executable` with informative reason).
  - Added unit and integration tests in `tests/test_browser_perception.py` verifying fingerprint stability despite D04 rotating banner, click action execution, and clean `not_executable` reporting on missing elements.
- **Untested**: Tape recorder and noise floor profiling (arrives in Prompt 2.2).
- **Risks**: None.

### Prompt 2.2: Tape Recorder and Noise Floor (2026-10-13)
- **Status**: Completed
- **Changes**:
  - Implemented `TapeRecorder` in `proofqa/tape/recorder.py`: append-only JSONL event writer (`tape.jsonl`), blob directory for HTTP JSON payloads <= 256KB (`blobs/`), Playwright tracing archive exporter (`traces/trace.zip`), and failure screenshot capture (`screenshots/`).
  - Added Playwright page listener integration: records `ActionEvent`, `NetworkEvent` (with first-party calculation derived from target world host), `ConsoleEvent`, `PageErrorEvent`, `StateEvent`, and `UiFactEvent`.
  - Implemented `Tape` container and parser in `proofqa/tape/tape.py`: loads and validates serialized JSONL event stream, preserves deterministic action order.
  - Implemented `signature_from_events()` extracting grounded `FailureSignature` instances (page errors, first-party 5xx responses, first-party console errors) normalized via `normalize_message()`.
  - Implemented `NoiseProfile` and `noise_floor()` in `proofqa/tape/noise.py`: runs dual-pass exploration on clean worlds to baseline pre-existing third-party console/network anomalies (such as Decoy D02 telemetry tracker failure).
  - Configured SPA fallback in `apps/shop_twin/backend/app.py` to route direct client page hits directly to `index.html`.
  - Added full test suite in `tests/test_tape.py`: tested 5-step journey recording & identical deserialization, failure signature derivation, blob sizing bounds, and confirmed clean twin noise profile isolates Decoy D02 while reporting 0 first-party errors.
- **Untested**: Replay engine and three-valued outcome evaluation (arrives in Prompt 2.3).
- **Risks**: None.

### Prompt 2.3: Replay Engine (2026-10-13)
- **Status**: Completed
- **Changes**:
  - Implemented `replay()` in `proofqa/proof/replay.py`: executes n deterministic replays across freshly instantiated isolated worlds and browser contexts, executing actions sequentially.
  - Implemented three-valued outcome classification: `FAIL` (target failure signature reproduced), `PASS` (ran fully without failure), and `UNRESOLVED` (action not executable, precondition missing, or timeout).
  - Implemented bounded parallel replay using `asyncio.Semaphore` and in-memory trace/world/signature SHA-256 memoisation (`_REPLAY_CACHE`).
  - Implemented signature locking comparison `signatures_match()` ensuring strict fidelity against target failure signatures.
  - Added `data-testid="modal-add-to-cart"` and `aria-label="Confirm Add to Cart"` in `apps/shop_twin/frontend/src/App.tsx` and updated frontend build.
  - Filtered third-party browser network errors (e.g. `ERR_NAME_NOT_RESOLVED` from Decoy D02 telemetry tracker) in `signature_from_events()`.
  - Added comprehensive tests in `tests/test_replay.py`: confirmed B01 scripted trace gives 2 of 2 `FAIL`, clean world gives 2 of 2 `PASS`, missing prerequisite step gives `UNRESOLVED` (never `PASS`), and B09 gives a mix of outcomes without `UNRESOLVED`. Verified import guards pass.
- **Untested**: State graph exploration and rule-based frontier (arrives in Phase 3, Prompt 3.1).
- **Risks**: None.

## Phase 3: Explorer (Track B)

### Prompt 3.1: State Graph and Rule-Based Explorer (2026-10-13)
- **Status**: Completed
- **Changes**:
  - Implemented `StateGraph` in `proofqa/explore/state_graph.py`: directed state graph powered by NetworkX and backed by SQLite persistence (`states` and `transitions` tables). Provides frontier management, nearest-untried state querying (`nx.shortest_path`), path reconstruction from root, and coverage metrics.
  - Implemented deterministic input library in `proofqa/explore/inputs.py`: handles valid strings, empty strings, very long buffers (1000 chars), unicode and emoji, single and double quote characters, zero, negative numbers, and huge boundary numbers, plus automatic test account generation.
  - Implemented `RuleBasedExplorer` in `proofqa/explore/explorer.py`: navigates the application frontier autonomously without LLM reliance, recording a unified session `Tape`, detecting adversarial loops (trap pages like `/trap/circular-*` and `/trap/infinite-scroll`), backtracking via clean-world resets (`world.reset()`), and exposing an extensible oracle hook interface.
  - Added tests in `tests/test_explorer.py`: verified multi-page state coverage reporting, SQLite graph persistence, deterministic action choice across identical seeds, and trap avoidance without infinite loops.
- **Untested**: LLM gateway and proposer integration (arrives in Prompt 3.2).
- **Risks**: None.




