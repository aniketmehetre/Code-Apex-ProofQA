"""Tests for frozen ProofQA contracts and normalize_message."""

import json
from pathlib import Path

from pydantic import TypeAdapter

from proofqa.contracts import (
    Action,
    ActionEvent,
    ActionKind,
    CertificateManifest,
    ConsoleEvent,
    FailureSignature,
    Finding,
    Locator,
    NetworkEvent,
    OracleClass,
    PageErrorEvent,
    ReplayOutcome,
    ReplayOutcomeKind,
    StateEvent,
    StateFingerprint,
    TapeEvent,
    Tier,
    UiFactEvent,
    VerifyVerdict,
    VerifyVerdictKind,
    WorldSpec,
    contracts_version,
    normalize_message,
)


def test_contracts_version():
    assert contracts_version == "1.1"


def test_normalize_message_uuids():
    msg = "User error with session 12345678-1234-1234-1234-123456789abc failed"
    norm = normalize_message(msg)
    assert norm == "User error with session <UUID> failed"


def test_normalize_message_timestamps():
    msg1 = "Occurred at 2026-10-24T09:15:30Z in module"
    msg2 = "Occurred at 12:45:00.123 in module"
    assert normalize_message(msg1) == "Occurred at <TIMESTAMP> in module"
    assert normalize_message(msg2) == "Occurred at <TIMESTAMP> in module"


def test_normalize_message_hex_and_digits():
    msg = "Memory pointer 0x7ffd9b8a with 42 items in buffer"
    norm = normalize_message(msg)
    assert norm == "Memory pointer <HEX> with <NUM> items in buffer"


def test_normalize_message_combined():
    raw = (
        "Server 500: Order 987654 failed at 2026-10-13 14:20:00 "
        "for tx 550e8400-e29b-41d4-a716-446655440000 addr 0xdeadbeef"
    )
    expected = (
        "Server <NUM>: Order <NUM> failed at <TIMESTAMP> "
        "for tx <UUID> addr <HEX>"
    )
    assert normalize_message(raw) == expected


def test_locator_roundtrip():
    loc = Locator(role="button", name="Add to Cart", testid="add-cart", css_fallback=".btn-add")
    serialized = loc.model_dump_json()
    deserialized = Locator.model_validate_json(serialized)
    assert loc == deserialized


def test_action_roundtrip():
    action = Action(
        id="act_01",
        kind=ActionKind.CLICK,
        locator=Locator(role="button", name="Checkout"),
        value="test_val",
        params={"timeout_ms": 5000},
    )
    serialized = action.model_dump_json()
    deserialized = Action.model_validate_json(serialized)
    assert action == deserialized


def test_state_fingerprint_roundtrip():
    fp = StateFingerprint(
        url_path="/cart",
        aria_hash="sha256:abc123aria",
        simhash="sim:998877",
        control_count=14,
    )
    serialized = fp.model_dump_json()
    deserialized = StateFingerprint.model_validate_json(serialized)
    assert fp == deserialized


def test_tape_events_roundtrip():
    adapter = TypeAdapter(TapeEvent)

    action_ev = ActionEvent(
        action=Action(id="a1", kind=ActionKind.GOTO, value="/shop"),
        timestamp_ms=100.5,
        duration_ms=45.2,
    )
    net_ev = NetworkEvent(
        method="POST",
        url="http://localhost:8000/api/cart",
        status=500,
        first_party=True,
        request_body_hash="sha256:bodyhash",
        response_blob_ref="blob_001.json",
        timestamp_ms=200.0,
    )
    console_ev = ConsoleEvent(
        level="error",
        text="Uncaught TypeError: cannot read properties of undefined",
        url="http://localhost:8000/main.js",
        timestamp_ms=250.0,
    )
    page_err_ev = PageErrorEvent(
        error_type="TypeError",
        message="Cannot read properties of null",
        stack="TypeError at app.js:10:14",
        timestamp_ms=300.0,
    )
    state_ev = StateEvent(
        fingerprint=StateFingerprint(
            url_path="/shop", aria_hash="h1", simhash="s1", control_count=5
        ),
        timestamp_ms=350.0,
    )
    ui_fact_ev = UiFactEvent(
        label="cart_count",
        ui_value=3,
        api_value=2,
        api_ref="api_blob_cart.json",
        timestamp_ms=400.0,
    )

    events = [action_ev, net_ev, console_ev, page_err_ev, state_ev, ui_fact_ev]
    for ev in events:
        json_str = adapter.dump_json(ev)
        deserialized = adapter.validate_json(json_str)
        assert ev == deserialized


def test_oracle_classes_and_tiers():
    assert set(c.value for c in OracleClass) == {"A", "B", "C", "D", "E", "F"}
    assert set(t.value for t in Tier) == {
        "VERIFIED",
        "VERIFIED_VIOLATION",
        "INTERMITTENT",
        "SUSPECTED",
        "INSUFFICIENT_EVIDENCE",
    }


def test_failure_signature_roundtrip():
    sig = FailureSignature(
        kind="http_5xx",
        first_party_endpoint="/api/cart",
        status=500,
        error_type="InternalServerError",
        message_norm="Server error: item <NUM> invalid",
        top_frame="cart.py:line_42",
    )
    serialized = sig.model_dump_json()
    deserialized = FailureSignature.model_validate_json(serialized)
    assert sig == deserialized


def test_replay_outcome_roundtrip():
    outcome = ReplayOutcome(
        outcome=ReplayOutcomeKind.FAIL,
        reason="Observed target 500 signature",
        reproduced=True,
        signature=FailureSignature(kind="http_5xx", status=500, message_norm="failed"),
        wall_time_ms=1230.5,
        attempt_log=[{"attempt": 1, "status": "FAIL"}],
    )
    serialized = outcome.model_dump_json()
    deserialized = ReplayOutcome.model_validate_json(serialized)
    assert outcome == deserialized


def test_world_spec_roundtrip():
    spec = WorldSpec(
        app="shop_twin",
        seed_db="apps/shop_twin/backend/seed.db",
        bugs=["B01", "B03"],
        seed=1337,
        clock_iso="2026-10-24T12:00:00Z",
        chaos={"latency_ms": 100},
    )
    serialized = spec.model_dump_json()
    deserialized = WorldSpec.model_validate_json(serialized)
    assert spec == deserialized


def test_finding_roundtrip():
    finding = Finding(
        id="FINDING-001",
        oracle_class=OracleClass.A,
        tier=Tier.VERIFIED,
        signature=FailureSignature(
            kind="http_5xx",
            first_party_endpoint="/api/cart",
            status=500,
            message_norm="POST /api/cart quantity <NUM> failed",
        ),
        claim="POST cart with quantity 0 returns 500",
        provenance="apps/shop_twin/backend/bugs.py",
        steps=[
            Action(id="s1", kind=ActionKind.GOTO, value="/shop"),
            Action(id="s2", kind=ActionKind.CLICK, locator=Locator(testid="add-btn")),
        ],
        confidence=1.0,
        intent_confirmation_needed=False,
    )
    serialized = finding.model_dump_json()
    deserialized = Finding.model_validate_json(serialized)
    assert finding == deserialized


def test_certificate_manifest_roundtrip():
    manifest = CertificateManifest(
        certificate_id="CERT-2026-001",
        finding_id="FINDING-001",
        created_at="2026-10-13T00:00:00Z",
        files={"claim.json": "sha256:abc", "repro.json": "sha256:def"},
        manifest_hash="sha256:final",
    )
    serialized = manifest.model_dump_json()
    deserialized = CertificateManifest.model_validate_json(serialized)
    assert manifest == deserialized


def test_verify_verdict_roundtrip():
    verdict = VerifyVerdict(
        verdict=VerifyVerdictKind.VALID,
        reason="Manifest integrity verified and 3 of 3 replays matched signature",
        checks=[
            {"check": "manifest_hash", "passed": True},
            {"check": "replays_reproduced", "count": 3, "required": 3},
        ],
        certificate_id="CERT-2026-001",
    )
    serialized = verdict.model_dump_json()
    deserialized = VerifyVerdict.model_validate_json(serialized)
    assert verdict == deserialized


def test_exported_schemas_valid():
    schema_dir = Path(__file__).resolve().parent.parent / "docs" / "schemas"
    assert schema_dir.exists()
    schemas = list(schema_dir.glob("*.json"))
    assert len(schemas) >= 15
    for s in schemas:
        data = json.loads(s.read_text(encoding="utf-8"))
        assert "type" in data or "$defs" in data or "anyOf" in data or "title" in data


def test_action_burst_serialization():
    """Prompt 8 Rule: burst is additive and optional (default=1 omitted from serialization)."""
    # 1. Default burst=1 omitted from model_dump and JSON
    a_default = Action(id="a1", kind=ActionKind.CLICK)
    assert a_default.burst == 1
    dump = a_default.model_dump()
    assert "burst" not in dump
    assert '"burst"' not in a_default.model_dump_json()

    # 2. burst > 1 included in model_dump and JSON
    a_burst = Action(id="a2", kind=ActionKind.CLICK, burst=5)
    assert a_burst.burst == 5
    assert a_burst.model_dump()["burst"] == 5
    assert '"burst":5' in a_burst.model_dump_json() or '"burst": 5' in a_burst.model_dump_json()

    # 3. Deserializing legacy JSON without burst sets default 1
    legacy_json = '{"id": "a3", "kind": "click", "locator": null, "value": null, "params": {}}'
    a_deser = Action.model_validate_json(legacy_json)
    assert a_deser.burst == 1


def test_existing_certificates_verify_byte_for_byte():
    """Prompt 8 Rule: test proving every certificate already in results/ still verifies byte for byte."""
    import hashlib
    results_dir = Path(__file__).resolve().parent.parent / "results"
    manifests = list(results_dir.rglob("manifest.json"))
    assert len(manifests) > 0, "Expected existing certificates in results/"

    for manifest_path in manifests:
        cert_dir = manifest_path.parent
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        for rel_file, expected_hash in manifest_data.get("files", {}).items():
            fpath = cert_dir / rel_file
            assert fpath.exists(), f"File {rel_file} missing in {cert_dir}"
            h = hashlib.sha256(fpath.read_bytes()).hexdigest()
            assert h == expected_hash, f"Hash mismatch for {rel_file} in {cert_dir}: expected {expected_hash}, got {h}"

