# ProofQA 2.0 Contracts Documentation

> **Status: FROZEN** at Milestone M0 (contracts_version = "1")  
> Any changes to these contracts must be accompanied by an entry in `docs/progress.md`.

## 1. Overview & Architecture Boundaries

ProofQA 2.0 defines strict, deterministic contracts using Pydantic v2 models in `proofqa/contracts.py`.
These models establish the single source of truth across perception, execution tapes, oracles, replay, shrinking, and cryptographic bug certificates.

Exported JSON schemas are maintained under `docs/schemas/`.

---

## 2. Perception & Action Models

### `Locator`
Multi-strategy locator supporting resilient role-based selectors with semantic fallbacks.
- `role`: Optional ARIA role (e.g. `button`, `link`, `textbox`).
- `name`: Accessible name.
- `label`: Associated label text.
- `testid`: Explicit `data-testid` attribute.
- `css_fallback`: Fallback CSS selector when semantic locators fail.

### `ActionKind` (Enum)
Deterministic set of browser interactions:
- `goto`, `click`, `fill`, `select`, `press`, `wait`

### `Action`
Atomic browser action execution unit:
- `id`: Unique action identifier.
- `kind`: Interaction kind (`ActionKind`).
- `locator`: Target element locator.
- `value`: Optional payload (for fill/select/press).
- `params`: Execution configuration (e.g. timeouts).

### `StateFingerprint`
Normalized page perception state signature:
- `url_path`: Route path stripped of volatile query params.
- `aria_hash`: Hash of the normalized accessibility tree.
- `simhash`: Locality-sensitive hash of textual layout.
- `control_count`: Number of actionable interactive controls.

---

## 3. Tape Events (`TapeEvent` Discriminated Union)

The append-only tape records the ground-truth sequence of execution. All tape events share a common discriminator field `type`:

1. **`ActionEvent`** (`type = "action"`):
   - `action`: The executed `Action`.
   - `timestamp_ms`, `duration_ms`.
2. **`NetworkEvent`** (`type = "network"`):
   - `method`, `url`, `status`, `first_party`.
   - `request_body_hash`: SHA-256 of request payload.
   - `response_blob_ref`: Reference to content blob in the tape blob store.
3. **`ConsoleEvent`** (`type = "console"`):
   - `level`: `log`, `warn`, `error`.
   - `text`, `url`, `timestamp_ms`.
4. **`PageErrorEvent`** (`type = "page_error"`):
   - `error_type`: Runtime error class (e.g. `TypeError`).
   - `message`, `stack`, `timestamp_ms`.
5. **`StateEvent`** (`type = "state"`):
   - `fingerprint`: Settled `StateFingerprint`.
6. **`UiFactEvent`** (`type = "ui_fact"`):
   - `label`: Semantic fact identifier (e.g. `cart_badge`).
   - `ui_value`: Rendered value from DOM.
   - `api_value`: Corresponding value from ground-truth API response.
   - `api_ref`: Blob reference to the supporting API response.

---

## 4. Oracle Families & Grounded Tiers

### `OracleClass` (Enum)
Declares the proof strength of bug evidence:
- **Class A**: Hard signals (5xx status codes, uncaught page errors, first-party console errors above noise floor).
- **Class B**: Metamorphic relations (monotonicity, subset invariants, round-trip invariants).
- **Class C**: Spec claims with exact text quotes from documentation.
- **Class D**: Cross-layer consistency (disagreements between rendered UI and API JSON).
- **Class E**: Temporal differential (behavioral drift across builds on identical traces).
- **Class F**: Custom and security invariants.

### `Tier` (Enum)
- `VERIFIED`: Replayed $k$ of $k$ on clean world with Class A or D.
- `VERIFIED_VIOLATION`: Replayed violation for Class B, C, or E requiring product intent confirmation.
- `INTERMITTENT`: Flaky or probabilistic defect with measured reproduction rate.
- `SUSPECTED`: Signal observed but unconfirmed.
- `INSUFFICIENT_EVIDENCE`: Abstention state suggesting the next experiment.

---

## 5. Failure Signatures & Normalization

### `normalize_message(msg: str) -> str`
Pure function that strips:
- ISO 8601 timestamps and time strings $\to$ `<TIMESTAMP>`
- UUIDv4 / UUID strings $\to$ `<UUID>`
- Hexadecimal addresses (`0x...`) and hex hashes $\to$ `<HEX>`
- Runs of numbers/digits $\to$ `<NUM>`
- Collapses extra whitespace.

### `FailureSignature`
Signature lock preventing replay slippage:
- `kind`: Signature category.
- `first_party_endpoint`: API endpoint path.
- `status`: HTTP status code (if network).
- `error_type`: Error class.
- `message_norm`: Output from `normalize_message`.
- `top_frame`: Top first-party callsite frame.

---

## 6. Replay, World & Findings

### `ReplayOutcome`
- `outcome`: `FAIL` (reproduced target signature), `PASS` (ran fully without error), `UNRESOLVED` (prerequisite missing, action not executable, or environment timeout).
- `reason`, `signature`, `wall_time_ms`, `attempt_log`.

### `WorldSpec`
Hermetic runtime specification:
- `app`: Target application name.
- `seed_db`: Path to pristine database seed.
- `bugs`: Active bug flags (e.g. `["B01", "B03"]`).
- `seed`: Pseudo-random seed.
- `clock_iso`: Fixed frozen time ISO string.
- `chaos`: Latency, bandwidth, and chaos failure parameters.

### `Finding`
Discovered defect ready for proof and shrinking:
- `id`, `oracle_class`, `tier`, `signature`, `claim`, `provenance`, `steps`, `confidence`, `intent_confirmation_needed`.

---

## 7. Certificates & Verification

### `CertificateManifest`
- `certificate_id`, `finding_id`, `created_at`, `contracts_version`.
- `files`: Mapping of relative paths to SHA-256 hashes (`manifest.json` anchors `claim.json`, `repro.json`, `signature.json`, `replay.json`, `world.json`, and evidence artifacts).
- `manifest_hash`: Root cryptographic digest.

### `VerifyVerdict`
Independent verification decision:
- `verdict`: `VALID`, `INVALID`, `TAMPERED`, `UNRESOLVED_ENV`.
- `reason`, `checks`, `certificate_id`.
