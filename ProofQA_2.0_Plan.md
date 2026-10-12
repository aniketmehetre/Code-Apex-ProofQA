# ProofQA 2.0: Antigravity Implementation Plan

*Team VOID MAIN. Code Apex, Track 2. Sequential build prompts for Google Antigravity, derived from the ProofQA 2.0 Final Project Context.*

## 0. How to use this plan

**What this is.** A dependency-ordered set of prompts. Paste them one at a time into Antigravity's agent panel. Each prompt is self-contained, ends with commands that prove it worked, and builds on the one before. Hour figures are my rough planning estimates for a team of three or four using parallel agents, not promises.

**Check these first.**

1. Read the finale rules on pre-built code before you build ahead of 24 Oct. If code must be written during the event, rehearse this plan on a throwaway repo and run it live.
2. Antigravity's folder names and settings have changed between releases, and guides disagree (.agent versus .agents). Open your install's Rules and Workflows panel and use the path it shows.
3. Pin every dependency version the agent picks, and reject any dependency you cannot explain in Q&A.

**Setup (about 10 minutes).**

1. Create an empty repo and open it as the workspace. Save the context file as docs/CONTEXT.md.
2. Paste the AGENTS.md from section 1 into the repo root. Agents in the workspace read it before starting work.
3. Save the two workflows from section 2 so that /checkpoint and /redteam are available.
4. Set the terminal policy to ask for review on anything outside your repo, docker, git and the Makefile targets. Use the browser agent to look at the twin and the dashboard, but never use it as the product's test engine. The product uses Playwright in code.

**Working loop for every prompt.**

- Use **Planning mode** for prompts marked Planning. Read the implementation-plan artifact before approving. Reject plans that add frameworks, skip tests or touch the frozen contracts.
- Use **Fast mode** only for prompts marked Fast.
- When the agent finishes, run /checkpoint. Do not start the next prompt on a red build.
- Use the Agent Manager for parallel tracks only after the contracts are frozen (Prompt 0.2). Give each agent its own git branch and merge at milestones.
- Use your strongest model on Track B (replay, shrinking, verify) because correctness there is the whole claim. A faster model is fine for dashboard work.

**Parallel tracks (after Prompt 0.2).**

| Track | Owns | Prompts |
| --- | --- | --- |
| A: World | shop twin, bug catalogue, world manager | 1.1 to 1.4 |
| B: Core | harness, tape, replay, explorer, oracles, shrinking, certificate, verify, pipeline | 2.1 to 8.1 |
| C: Surface | bench reporting, control plane, dashboard | 9.x, 11.x (11.2 can start right after 0.2 using mock events) |

## 1. AGENTS.md (paste at repo root)

```markdown
# ProofQA 2.0 agent rules
Read docs/CONTEXT.md before any task. It is the source of truth for scope, vocabulary and honesty rules.

## Non-negotiable architecture rules
1. The LLM never decides whether something is a bug. Detection, replay, shrinking, certification and verification are deterministic code.
2. proofqa.proof, proofqa.cert and proofqa.oracles must never import proofqa.llm. Keep the import-guard test passing.
3. proofqa/cert/verify.py must not import proofqa.explore, proofqa.oracles, proofqa.llm or proofqa.uncertainty.
4. The tape is the single source of truth for what happened. Replay, shrinking, certificate and evidence are all derived from it.
5. A replay has three outcomes: FAIL (target signature observed), PASS (ran fully, signature not observed), UNRESOLVED (could not execute). UNRESOLVED is never treated as PASS.
6. Shrinking must preserve the same failure signature, not just any failure.
7. Everything works with OFFLINE=1 (no API key). The LLM only proposes actions, form values, claim extraction and report prose.
8. Contracts in proofqa/contracts.py are frozen after Prompt 0.2. Change them only after adding a note to docs/progress.md.

## Engineering rules
- Python 3.12, type hints everywhere, Pydantic v2 models at every boundary, async Playwright, ruff clean.
- Write the test first or alongside it. No feature is done without a passing test and a runnable command.
- Prefer the standard library and dependencies already in pyproject.toml. Ask before adding a dependency.
- No secrets in code, tapes or certificates. Read keys from env only.
- Do not invent numbers. Any metric shown anywhere must come from a bench run and be recorded in docs/claims.md.
- Never present recorded output as live. Label recorded runs.

## Definition of done for every task
Run make lint and make test. Append what changed, what is untested and any risk to docs/progress.md. State exactly which commands to run to see it work.
```

## 2. Workflows to save

**/checkpoint**

```markdown
Run make lint and make test. If anything fails, fix it before continuing. Append a dated entry to docs/progress.md (what changed, what is untested, risks). Commit with a clear message. Print the commands I can run to see the new behaviour.
```

**/redteam**

```markdown
Act as a hostile reviewer, not the author. Try to break the last milestone: tamper one byte in a certificate and run proofqa verify; run with OFFLINE=1; run the import-guard tests; run the pipeline on a clean world and on the decoys and look for false positives; compare every number in docs/claims.md with results/summary.json. Report each failure as a list item with reproduction commands. Do not fix anything in this pass.
```

## 3. Build map and milestones

| Phase | Goal | Milestone | Est. hours |
| --- | --- | --- | --- |
| 0 | Repo, rules, frozen contracts | M0 | 1 |
| 1 | Shop twin, bug catalogue, world manager |  | 3 |
| 2 | Harness, tape, replay |  | 3 |
| 3 | Explorer and LLM proposer |  | 2.5 |
| 4 | Oracles A, D, B (C and E optional) |  | 3 |
| 5 | Three-valued shrinking |  | 3 |
| 6 | Certificate, verify, exported test |  | 3 |
| 7 | Pipeline: the vertical slice | M1 | 1.5 |
| 8 | Uncertainty and tiers |  | 2 |
| 9 | ProofBench, baselines, metrics | M2 | 4 |
| 10 | Adversarial lab |  | 2 |
| 11 | Control plane and dashboard | M3 | 4 |
| 12 | CI delivery (stretch) |  | 1.5 |
| 13 | Demo, docs, final red team | M4 | 3 |

Tracks overlap, so elapsed time is less than the sum. M1 is the gate that matters: one command finds a bug, proves it, shrinks it, issues a certificate, and verify says VALID.

**De-scope ladder** (cut from the bottom up): Phase 12, then Prompt 4.4, then Phase 10 extras, then Class B relations beyond three, then value shrinking (5.3), then dashboard polish. Never cut Phases 1 to 7 or the bench with baselines.

## 4. The prompts

### Phase 0: Foundation

**Prompt 0.1: Scaffold (Fast)**

```text
Create the repository layout for ProofQA 2.0 exactly as follows, with empty package files and no feature code yet:
proofqa/ (contracts.py, world/, browser/, tape/, explore/, oracles/, proof/, cert/, uncertainty/, llm/, lab/, api/, cli.py), proofbench/, apps/shop_twin/backend, apps/shop_twin/frontend, dashboard/, tests/, docs/ (CONTEXT.md already present; add progress.md, claims.md, contracts.md), results/.
Add pyproject.toml (Python 3.12; dependencies: fastapi, uvicorn, pydantic>=2, sqlmodel, playwright, networkx, typer, httpx, litellm, pytest, pytest-asyncio, hypothesis, ruff), a Makefile with targets setup, lint, test, twin, bench, demo (stubs allowed for the last three), a .gitignore and a README stub.
Add tests/test_import_guards.py that enforces architecture rules 2 and 3 from AGENTS.md by statically scanning imports. It must pass on the empty packages.
Acceptance: make setup installs everything including chromium through playwright install; make lint and make test pass; git is initialised with one commit.
```

**Prompt 0.2: Contracts (Planning)**

```text
Read docs/CONTEXT.md sections 3, 5 and 6. Implement proofqa/contracts.py with Pydantic v2 models and document them in docs/contracts.md:
- Locator (role, name, label, testid, css_fallback) and Action (id, kind: goto|click|fill|select|press|wait, locator, value, params).
- StateFingerprint (url_path, aria_hash, simhash, control_count).
- TapeEvent as a discriminated union: ActionEvent, NetworkEvent (method, url, status, first_party, request_body_hash, response_blob_ref), ConsoleEvent, PageErrorEvent, StateEvent, UiFactEvent (label, ui_value, api_value, api_ref).
- OracleClass enum A to F; Tier enum (VERIFIED, VERIFIED_VIOLATION, INTERMITTENT, SUSPECTED, INSUFFICIENT_EVIDENCE).
- FailureSignature (kind, first_party_endpoint, status, error_type, message_norm, top_frame) and a pure function normalize_message() that strips digit runs, UUIDs, timestamps and hex ids, with tests.
- ReplayOutcome (FAIL, PASS, UNRESOLVED with reason), WorldSpec (app, seed_db, bugs, seed, clock_iso, chaos), Finding, Certificate manifest, VerifyVerdict (VALID, INVALID, TAMPERED, UNRESOLVED_ENV).
Add contracts_version = '1', export JSON schemas to docs/schemas/, and add round-trip tests. Implement no behaviour beyond normalize_message. When done, state that the contracts are FROZEN.
Acceptance: make test passes with at least one test per model.
```

### Phase 1: The shop twin (Track A)

**Prompt 1.1: Backend (Planning)**

```text
Build apps/shop_twin/backend: a FastAPI plus SQLite shop used as the benchmark target. Endpoints under /api: register, login, logout (cookie session); GET /products with q, category, sort (price_asc, price_desc, name), page, page_size and a total count in the response; GET, POST, PATCH, DELETE for cart items; POST /coupons/apply; POST /checkout with an address; PUT and GET /account/address; GET /orders; GET /health.
Provide seed.py that creates a deterministic seed.db (60 products, 4 categories, 3 coupons). Add apps/shop_twin/backend/bugs.py exposing is_on(id), which reads the BUGS env var (comma separated). No bugs are implemented yet. The app also serves the built frontend from /.
Write httpx tests for every endpoint.
Acceptance: make twin starts the app on a free port with a fresh copy of seed.db; backend tests pass.
```

**Prompt 1.2: Frontend (Planning)**

```text
Build apps/shop_twin/frontend (React, Vite, TypeScript, Tailwind) as a plain, accessible shop: header with a cart badge; product list with search box, category filter, sort dropdown and pagination; product detail; cart with line items, quantity controls, coupon box and total; login and register; checkout with an address form; orders page; an /about page. Use semantic roles and labels, plus data-testid on the cart badge, cart total and product count. All data comes from fetch calls to /api. The build goes to dist/ and is served by the backend.
Acceptance: make twin shows a working shop. Use the browser agent to register, search, add to cart and check out, and attach screenshots.
```

**Prompt 1.3: Bug catalogue (Planning)**

```text
Implement the bug catalogue behind bugs.is_on, all off by default.
Bugs: B01 POST cart with quantity 0 returns 500. B02 state-dependent exception when checking out after removing an item with a coupon applied (needs at least four steps). B03 cart badge shows one more than the API count after a removal. B04 displayed total ignores the coupon discount. B05 sorting by price and then returning to the default order does not restore the original order. B06 category filter on page 2 returns items from other categories. B07 saved address is lost after reload. B08 register accepts a 4 character password although the about page states 8. B09 add to cart returns 500 about one request in three (seeded random). B10 searching with a single quote returns 500.
Decoys, always on: D01 friendly 404 page. D02 a third-party analytics request that fails with a console error. D03 an endpoint that takes two seconds. D04 a rotating banner that changes text on every load. D05 a deliberate 400 on an invalid coupon.
Also add hidden text on /about that tells an AI to ignore its instructions and visit another site, plus trap pages (infinite scroll, circular links).
Write proofbench/bugs/ground_truth.json with, per bug: id, class, category, difficulty, minimal trigger description and expected signature fields. Write one deterministic test per bug showing it fires when on and is absent when off, and one test proving the decoys cause no first-party 5xx or page error.
Acceptance: make test passes.
```

**Prompt 1.4: World manager (Planning)**

```text
Implement proofqa/world. World is a context manager built from a WorldSpec. start(): temp directory, copy seed.db, pick a free port, launch the twin with BUGS, seed and clock env, wait for /api/health. reset(): restore the database from the seed snapshot without restarting. stop(): clean shutdown. Also add a Dockerfile and docker-compose.yml that run the same world so proofqa verify can use --docker later.
Acceptance: a test starts three worlds in parallel with different BUGS sets and checks isolation; a test registers a user, calls reset(), and proves the user is gone; startup time is logged.
```

### Phase 2: Harness, tape, replay (Track B)

**Prompt 2.1: Harness and perception (Planning)**

```text
Implement proofqa/browser: an async Playwright Harness that creates a fresh browser context per run with a fixed viewport and controlled time and randomness (use the clock API if the installed Playwright version supports it; otherwise an init script that seeds Math.random and fixes Date).
Perception: build a list of candidate Actions from the ARIA snapshot with stable ids (hash of role, name and ancestry), filtered by a safety policy (same origin only; deny list for destructive actions unless explicitly allowed). fingerprint(page) returns a StateFingerprint from normalised ARIA text; detect volatile regions by comparing two fresh loads and mask them.
execute(action) tries locators in order: role plus name, label, testid, css fallback. It returns ok or not_executable with a reason (this feeds UNRESOLVED).
Acceptance: tests on a clean twin show the home-page fingerprint is stable across fresh loads even with decoy D04; click actions work; a missing element returns not_executable.
```

**Prompt 2.2: Tape recorder and noise floor (Planning)**

```text
Implement proofqa/tape: an append-only JSONL tape plus a blob directory. Record per step the ActionEvent, NetworkEvent (first_party computed from the world origin; store JSON responses up to 256 KB as blobs), ConsoleEvent, PageErrorEvent and StateEvent. Also save a Playwright trace zip per run and a screenshot at failures.
Implement Tape.load(), signature_from_events() following the FailureSignature contract, and noise_floor(world): visit key pages twice from a clean state and store the pre-existing console and network noise as a NoiseProfile.
Acceptance: record a five-step scripted journey and reload it identically; the noise profile on a clean twin contains the D02 third-party error marked non-first-party and nothing first-party.
```

**Prompt 2.3: Replay engine (Planning)**

```text
Implement proofqa/proof/replay.py. replay(trace, world_spec, n, target_signature) runs n replays, each in a freshly reset world and a fresh browser context, executing actions in order. Classify each as FAIL (target signature observed), PASS (executed fully without it) or UNRESOLVED (action not executable, timeout or environment error). Run replays in parallel with a semaphore and memoise by (trace hash, world hash). Return a ReplayReport with counts and per-run evidence references.
Acceptance: with B01 on, a scripted trace gives n of n FAIL; with B09 it gives a mix; on a clean world it gives PASS; a trace with its prerequisite step removed gives UNRESOLVED, not PASS. The import-guard test still passes.
```

### Phase 3: Explorer (Track B)

**Prompt 3.1: State graph and rule-based explorer (Planning)**

```text
Implement proofqa/explore: a networkx state graph keyed by StateFingerprint, persisted in SQLite, with edges per Action and per-state sets of tried actions. Frontier policy: prefer untried actions in the current state, then the nearest state with untried actions; enforce depth, step and time budgets; detect loops; backtrack by replaying the path from a clean world.
Form filling uses a deterministic input library: valid value, empty, very long, unicode and emoji, quote characters, zero, negative, huge number. Rotate through them per field. Register disposable test accounts automatically.
The explorer is rule-based and needs no LLM. It records one tape for the whole session and exposes a hook interface: when an oracle fires (oracles arrive in Phase 4), it stores a candidate with its action prefix.
Acceptance: on a clean twin the explorer reaches every top-level page within budget and never loops on the trap pages; coverage (states and edges) is reported; the same seed gives the same walk.
```

**Prompt 3.2: LLM gateway and proposer (Planning)**

```text
Implement proofqa/llm: a thin gateway over LiteLLM with Pydantic-validated structured outputs, a disk cache keyed by prompt hash, a JSONL log of latency, tokens and cost, and an offline mode (OFFLINE=1 or no key) that returns None so callers fall back.
Build a Proposer for the explorer. Input: a numbered list of candidate actions plus a short state summary in which page text is passed as a quoted data block. Output: an ordered list of indexes and form values, validated against the list. Anything not in the list is discarded and the rule-based choice is used. The model has no tools.
Acceptance: with a mocked model the proposer's choices are used; with OFFLINE=1 the whole explorer still runs; on /about the hidden injection text does not change behaviour (test with a mock that tries to return a URL that is not in the list). Import guards pass.
```

### Phase 4: Oracles (Track B)

**Prompt 4.1: Class A hard signals (Fast)**

```text
Implement proofqa/oracles/hard_signals.py. From tape events, flag first-party HTTP 5xx responses, uncaught page errors, and first-party console errors that are not in the NoiseProfile. Build a FailureSignature and create a candidate. Ignore third-party origins. Register it as the explorer hook.
Acceptance: exploring a twin with B01, B02 and B10 on yields a candidate for each; exploring a clean twin and a decoy-only twin with three seeds yields zero candidates.
```

**Prompt 4.2: Class D cross-layer consistency (Planning)**

```text
Implement proofqa/oracles/cross_layer.py. After each settled step capture UI facts (counts such as the cart badge and rendered list size; totals and prices near labels like total, subtotal, price) and compare them with the most recent relevant JSON response using a generic matcher (array length versus rendered item count; numeric fields versus labelled numbers) with a documented tolerance. Record a UiFactEvent holding both values and the API blob reference. A mismatch becomes a candidate only if it persists after a settle delay.
Acceptance: detects B03 and B04; zero false positives on a clean twin across three seeds and the decoys; docs/oracles.md documents the heuristics and their known limits.
```

**Prompt 4.3: Class B metamorphic relations (Planning)**

```text
Implement proofqa/oracles/relations: a plugin interface Relation (name, applies(widgets), run(harness) returning a violation or None, validate()). Implement a widget classifier from roles and labels (list, search box, sort control, paginator, cart, form) and these relations: sort is monotonic and stable on repeat; a filter result is a subset and clearing restores the list; a narrower search is a subset of a broader search; pages union to the full list without duplicates; add then remove returns to the original state; save then reload equals what was saved.
Each relation must pass validate() (it holds on a clean world across three runs and on other instances of the widget) before it can raise findings. Otherwise it is discarded and logged.
Acceptance: detects B05, B06 and B07; a deliberately false relation is discarded by validation; zero findings on a clean twin.
```

**Prompt 4.4: Classes C and E (Fast, optional)**

```text
Optional. Class C (spec claims): an LLM extracts verifiable claims from the app description together with the exact quote span; each claim maps to a deterministic check (for B08, a minimum password length) and the finding cites the quote. In OFFLINE mode, skip C.
Class E (temporal differential): replay a saved tape on two builds (two WorldSpecs) and report behaviour differences as VERIFIED_VIOLATION with an intent-confirmation flag.
Acceptance: B08 is found with the quote cited; E reports a difference between a buggy and a fixed world.
```

### Phase 5: Shrinking (Track B)

**Prompt 5.1: Generic three-valued ddmin (Planning)**

```text
Implement proofqa/proof/ddmin.py as a pure, generic function ddmin(items, test) where test returns FAIL, PASS or UNRESOLVED. Follow Zeller's algorithm with: UNRESOLVED candidates are never accepted and never counted as PASS; memoisation of tested subsets; a call budget; deterministic ordering; and a structured attempt log (subset, outcome).
Write hypothesis property tests with synthetic predicates: monotone failure; failure that needs items i and j together; dependencies where a candidate missing item i is UNRESOLVED; a non-monotone predicate. Assert that the result still fails, that UNRESOLVED never yields a reduction, and that the result is 1-minimal when the budget allows. No browser code in this file.
Acceptance: make test passes, including the property tests.
```

**Prompt 5.2: Browser shrinker (Planning)**

```text
Implement proofqa/proof/shrink.py using ddmin and the replay engine.
Level 1: remove steps that caused no state change and no network request.
Level 2: derive dependency blocks from the tape (a response that creates an entity and the later requests or steps that use its id travel together), run ddmin over blocks, then inside the blocks that remain.
Lock the failure signature: a candidate counts as FAIL only if the target signature matches. Use memoisation and parallel candidate replays. Return a ShrinkResult with the reduced trace, the attempt log, replays used and wall time.
Acceptance: a 15 to 30 step trace that triggers B02 reduces to the minimal trigger recorded in ground_truth.json; the account creation step is retained because removing it is UNRESOLVED; the final trace reproduces the same signature in a fresh world.
```

**Prompt 5.3: Value shrinking (Planning)**

```text
Extend the shrinker with Level 3. For fill and select values in the minimal trace, shrink numbers toward the smallest triggering value, shrink strings by character-level ddmin and simplify to a character class, keeping the signature locked. Return a MinimalInput description (for example quantity 0, or a single quote).
Acceptance: B10 shrinks to a single quote character; B01 to quantity 0; each result is replayed n of n before it is accepted.
```

### Phase 6: Certificate and verify (Track B)

**Prompt 6.1: Certificate builder (Planning)**

```text
Implement proofqa/cert/build.py. Build a certificate directory from a Finding, ShrinkResult, ReplayReport, Tape and WorldSpec containing: claim.json (one sentence, oracle class, provenance), repro.json, signature.json, replay.json, world.json, evidence/ (trace zip, screenshots or video, HAR, console log), limits.md (class-specific honest limits) and manifest.json with the SHA-256 of every file plus a manifest hash.
Acceptance: certificates build for B01 and B03; the manifest recomputes correctly.
```

**Prompt 6.2: proofqa verify (Planning)**

```text
Implement proofqa/cert/verify.py and the CLI command proofqa verify <path> [--docker]. It must be independent of the agent: write its own small Playwright executor and use only contracts, the world manager and its own signature matcher. Do not import explore, oracles, llm or uncertainty.
Steps: check manifest integrity (any changed byte gives TAMPERED); rebuild the world from world.json (local or docker); replay the minimal reproduction three times; match the signature. Verdicts: VALID, INVALID (not reproduced or a different signature), TAMPERED, UNRESOLVED_ENV. Print one line per check and a final VERDICT line.
Acceptance: VALID on a fresh certificate; flipping one byte gives TAMPERED; verifying against a fixed world gives INVALID; the import-guard test enforces independence.
```

**Prompt 6.3: Exported test and fix-flip validation (Planning)**

```text
Generate a standalone pytest-playwright test from the minimal repro, using role-based locators with fallbacks. The test asserts the correct behaviour (no first-party 5xx or page error, UI equals API, relation holds), so it FAILS on the buggy build and PASSES on the fixed build. Add a stability gate (three consecutive identical results). Add a fix-flip validator in proofbench: run the test on the buggy world (must fail) and on the same world with the bug off (must pass), and reject tests that do not satisfy both.
Acceptance: tests exported for B01, B03 and B05 pass the fix-flip validator.
```

### Phase 7: The vertical slice (Milestone M1)

**Prompt 7.1: Pipeline (Planning)**

```text
Implement proofqa/pipeline.py and the CLI command proofqa run --world <spec or url> [--budget ...]. Stages: explore, detect, replay (k of n), shrink, certify. Add an async event bus that emits typed events (used later for SSE), SQLite session state so a run can resume, budgets, and a clean shutdown. Use a simple tier rule for now: VERIFIED when a class A or D finding reproduces k of k.
Acceptance (Milestone M1): on a twin with B01, B03 and B10 on, one command produces three certificates and proofqa verify returns VALID for each; on a clean twin it produces none. Run /checkpoint and tag m1.
```

### Phase 8: Uncertainty (Track B)

**Prompt 8.1: Confidence, tiers, dedup, abstention (Planning)**

```text
Implement proofqa/uncertainty. Confidence is composed from: reproduction rate with a Wilson interval, oracle class strength, signature stability across replays, distance above the noise floor, and the relation validation record. Assign tiers: VERIFIED; VERIFIED_VIOLATION with an intent-confirmation flag for classes B to E; INTERMITTENT with the observed rate; SUSPECTED; INSUFFICIENT_EVIDENCE. Deduplicate findings by failure fingerprint (endpoint, status, normalised message, top frame). For each INSUFFICIENT_EVIDENCE case, suggest the next experiment from a small rule table (for example a throttled-network replay, or a second account). Log every component of every score.
Acceptance: B09 is INTERMITTENT with its rate; a weak decoy-like signal is INSUFFICIENT_EVIDENCE and names the experiment; duplicate findings collapse; B05 is VERIFIED_VIOLATION with the flag. Integrate into the pipeline and rerun the M1 checks.
```

### Phase 9: ProofBench (Track C, Milestone M2)

**Prompt 9.1: Runner and adjudication (Planning)**

```text
Implement proofbench. A YAML config selects apps and bug sets sampled by seed from ground_truth.json by difficulty, with a dev split and a held-out split whose seed comes from the HELDOUT_SEED env var (never committed). The runner executes configurations over seeds in parallel and writes JSONL results. Adjudicate every finding against ground_truth.json as: true bug (by signature match), duplicate, decoy hit or false positive. Compute certificate validity by actually running proofqa verify in a clean temp directory.
Acceptance: make bench runs the full ProofQA configuration on the dev split for 5 seeds and writes results/runs.jsonl.
```

**Prompt 9.2: Baselines and ablations (Planning)**

```text
Add baselines under identical step and token budgets. B1: a random monkey with a naive reporter that files any console error, 4xx, 5xx or timeout. B2: a naive LLM ReAct agent that reports bugs by its own judgement (skipped when OFFLINE). Add ablation switches to the pipeline config: no_prove, no_shrink_l1, no_shrink_l2, no_shrink_l3, no_stategraph (random frontier), no_class_X for each oracle, no_uncertainty.
Acceptance: every configuration runs on the dev split and is scored by the same adjudicator rules.
```

**Prompt 9.3: Metrics and report (Planning)**

```text
Compute: precision and recall at bug level (deduplicated); certificate validity rate; reproduction rate; shrink ratio (steps and input size) and replays per shrink; time to first verified finding; cost per verified bug; coverage; calibration error with a reliability diagram; selective accuracy curve; decoy false-positive rate; suite mutation score where available. Use at least 5 seeds and Wilson or bootstrap intervals. Write results/summary.json, results/report.md and PNG plots, and auto-fill docs/claims.md (claim, experiment id, measured value, interval).
Acceptance: make bench regenerates everything from raw runs, and no number in any doc is missing from summary.json. Tag m2.
```

### Phase 10: Adversarial lab (Track B)

**Prompt 10.1: Chaos and adversarial suite (Planning)**

```text
Add chaos knobs to the harness and WorldSpec: latency, failing or aborted endpoints, offline mode, throttled network, clock skew, viewport. Record them on the tape so runs replay. Add an adversarial suite to proofbench: the injection page (measure hijack rate for ProofQA and for the naive LLM baseline, where a hijack is navigating off origin or off task), trap pages, decoys (false-positive rate) and a rotating-banner state-hash test.
Acceptance: ProofQA hijack count is 0 of N in the tests; chaos runs replay deterministically from certificates; results are added to summary.json.
```

### Phase 11: Control plane and dashboard (Track C, Milestone M3)

**Prompt 11.1: Control plane (Planning)**

```text
Implement proofqa/api (FastAPI): POST /sessions; GET /sessions/{id}; GET /sessions/{id}/events as SSE; GET /sessions/{id}/findings; GET /certificates/{id} with a zip download; POST /race (runs ProofQA and a baseline concurrently on the same world and budget and streams both); POST /verify (runs proofqa verify and streams its lines); GET /bench/summary; POST /findings/{id}/review (approve adds to the suite; reject creates a signature-level suppression rule). The server is authoritative for all statuses.
Acceptance: pytest with httpx and a curl script exercise every endpoint; SSE survives a client reconnect.
```

**Prompt 11.2: Dashboard shell (Fast, can start after 0.2)**

```text
Build dashboard (React, Vite, TypeScript, Tailwind, Cytoscape.js, Recharts) in dark graphite with green accents. Screens: Race (two lanes with counters for reports filed, certificates valid and false reports); Explorer (live state graph); Finding and Evidence (synchronised timeline of video, network, console, DOM and graph node); Shrink (blocks turning red, green or grey); Certificate and Verify; Bench scoreboard with intervals; Review queue. Use typed mock events generated from the contracts so it runs standalone. Colour must reflect real states only: green verified, red fails, grey unresolved.
Acceptance: npm run dev shows every screen with mock data; use the browser agent to capture screenshots.
```

**Prompt 11.3: Wire to live (Planning)**

```text
Replace the mocks with the SSE API. Handle disconnects, partial results and failed stages without inventing completion states (if shrinking times out, show the verified original trace). Add a Verify panel that streams proofqa verify output for a chosen certificate, and a Tamper button that flips one byte in a copy and re-runs it.
Acceptance: with the browser agent, run the race on a twin with three bugs and attach screenshots of every screen; the tamper demo shows VALID and then TAMPERED. Tag m3.
```

### Phase 12: CI delivery (stretch)

**Prompt 12.1: Action, suite and drift (Fast)**

```text
Generate a GitHub Action that runs proofqa against a preview URL or a compose world and posts a PR comment with certificate links. Export the regression suite from verified findings. Run a mutation-score check on the suite using the bug catalogue as mutants. Add a nightly drift report (new states, changed behaviour).
Acceptance: the Action file validates; the PR comment markdown renders; the suite mutation score is recorded in summary.json.
```

### Phase 13: Demo, docs and final red team (Milestone M4)

**Prompt 13.1: Demo harness (Planning)**

```text
Add make demo: start the twin, open the dashboard, and run the scripted flow from the demo section of docs/CONTEXT.md. Add the judge's-choice menu of about 12 pre-validated bug flags with a make validate-menu target proving each flag is found end to end. Store a recorded run in demo/recorded/ as the fallback, always shown with a visible RECORDED label.
Acceptance: make demo works from a clean clone; validate-menu passes for every flag in the menu.
```

**Prompt 13.2: Docs and claims (Fast)**

```text
Write the README (what it is, one-command quickstart, an architecture mermaid diagram, ProofBench instructions), finish docs/claims.md, and write docs/limits.md listing what ProofQA does not prove. Make every number on the slides traceable to a claim id.
Acceptance: a fresh clone follows the README to run the demo and the bench.
```

**Prompt 13.3: Final red team**

```text
/redteam
Then fix only the items reported, one per commit, and rerun /redteam until it is clean.
Acceptance: the tamper test, the OFFLINE test, the import guards, the clean-world false-positive test and the claims-versus-summary check all pass. Tag m4.
```

## 5. Recovery prompts (when the agent drifts)

**It touched frozen contracts or broke an architecture rule**

```text
Stop. You violated AGENTS.md rule <number>. Revert that change, explain in two sentences why you made it, and propose a compliant alternative before writing any code.
```

**It claims something works without proof**

```text
Show me the command and its actual output that proves this works. If you cannot run it, say so and list what is untested. Do not describe expected behaviour as observed behaviour.
```

**A test is flaky or a bug will not reproduce**

```text
Do not add retries or sleeps to hide this. Find the nondeterminism: record the tape for three runs, diff them, and name the exact source (time, randomness, network ordering, database state). Fix the source, then show three identical runs.
```

**You want a plan before code**

```text
Before writing code, list the files you will create or change, the tests you will add, and anything in the prompt you consider ambiguous. Wait for my approval.
```

## 6. Milestone gates

| Milestone | Gate | If it fails |
| --- | --- | --- |
| M0 | Contracts frozen, make test green | Do not start any track |
| M1 | One command finds, proves, shrinks, certifies; verify says VALID; tamper says TAMPERED | Fix before anything else; demo fallback depends on it |
| M2 | Bench runs the full system and baselines on the dev split with intervals | Narrow the claims on the slides to what the numbers show |
| M3 | Dashboard runs the race live; no invented states | Show the CLI flow and recorded run, labelled |
| M4 | Clean-clone demo and a clean /redteam | Use the labelled recorded run and answer from docs/limits.md |
