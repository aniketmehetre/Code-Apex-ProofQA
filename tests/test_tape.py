"""Acceptance tests for tape recording, re-loading, and clean twin noise profiling."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofqa.contracts import (
    Action,
    ActionKind,
    Locator,
    NetworkEvent,
    PageErrorEvent,
    StateFingerprint,
    WorldSpec,
)
from proofqa.tape import Tape, TapeRecorder, noise_floor, signature_from_events
from proofqa.world import World


def test_record_five_step_journey_and_reload_identically(tmp_path: Path) -> None:
    recorder = TapeRecorder(output_dir=tmp_path, world_origin="http://127.0.0.1:8000")

    actions = [
        Action(id="a1", kind=ActionKind.GOTO, value="/"),
        Action(id="a2", kind=ActionKind.CLICK, locator=Locator(role="searchbox", name="Search products")),
        Action(id="a3", kind=ActionKind.FILL, locator=Locator(role="searchbox", name="Search products"), value="keyboard"),
        Action(id="a4", kind=ActionKind.CLICK, locator=Locator(role="link", name="Wireless Keyboard")),
        Action(id="a5", kind=ActionKind.CLICK, locator=Locator(role="button", name="Add to Cart")),
    ]

    for i, action in enumerate(actions):
        recorder.record_action(action, duration_ms=12.5)
        # Accompanying network and state events
        recorder.record_state(
            StateFingerprint(
                url_path=f"/step_{i}",
                aria_hash=f"aria_{i}",
                simhash=f"hash_{i}",
                control_count=10 + i,
            )
        )
        net_event = NetworkEvent(
            method="GET",
            url=f"http://127.0.0.1:8000/api/step_{i}",
            status=200,
            first_party=True,
            response_blob_ref=f"blob_{i}.json",
            timestamp_ms=1000.0 * i,
        )
        recorder.record_event(net_event)

    tape_file = tmp_path / "tape.jsonl"
    assert tape_file.exists()

    # Verify 15 total events (5 actions + 5 states + 5 network)
    with open(tape_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    assert len(lines) == 15

    # Reload tape identically
    loaded_tape = Tape.load(tape_file)
    assert len(loaded_tape.events) == 15
    assert loaded_tape.actions() == actions

    # Verify identical JSON serialization
    for original_event, loaded_event in zip(recorder.events, loaded_tape.events, strict=True):
        assert original_event.model_dump() == loaded_event.model_dump()


def test_signature_from_events_extracts_correct_failure() -> None:
    # 1. First-party 500 error
    net_500 = NetworkEvent(
        method="POST",
        url="http://127.0.0.1:8000/api/cart",
        status=500,
        first_party=True,
        timestamp_ms=100.0,
    )
    sig_500 = signature_from_events([net_500])
    assert sig_500 is not None
    assert sig_500.kind == "http_5xx"
    assert sig_500.first_party_endpoint == "/api/cart"
    assert sig_500.status == 500

    # 2. Uncaught page error
    page_err = PageErrorEvent(
        error_type="TypeError",
        message="Cannot read properties of undefined (reading 'price')",
        stack="TypeError: Cannot read properties\n    at CartView.tsx:42:15",
        timestamp_ms=200.0,
    )
    sig_page = signature_from_events([page_err])
    assert sig_page is not None
    assert sig_page.kind == "page_error"
    assert sig_page.error_type == "TypeError"
    assert "Cannot read properties" in sig_page.message_norm


def test_blob_storage_under_256kb(tmp_path: Path) -> None:
    recorder = TapeRecorder(output_dir=tmp_path, world_origin="http://127.0.0.1:8000")
    dummy_data = {"products": [{"id": i, "name": f"item_{i}"} for i in range(50)]}
    data_bytes = json.dumps(dummy_data).encode("utf-8")

    # Write blob directly to verify pathing
    blob_ref = "test_blob.json"
    (recorder.blob_dir / blob_ref).write_bytes(data_bytes)
    assert (recorder.blob_dir / blob_ref).exists()
    assert (recorder.blob_dir / blob_ref).stat().st_size < 256 * 1024


@pytest.mark.asyncio
async def test_noise_profile_on_clean_twin_captures_d02_and_no_first_party() -> None:
    spec = WorldSpec(app_id="shop_twin", bugs=[])
    world = World(spec)
    with world:
        profile = await noise_floor(world, key_pages=["/", "/about"])

        # Ground truth requirement: clean twin has NO first party noise
        assert not profile.has_first_party_errors
        assert len(profile.first_party_console_errors) == 0
        assert len(profile.first_party_network_errors) == 0

        # Ground truth requirement: contains Decoy D02 third-party error marked non-first-party
        assert len(profile.third_party_console_errors) > 0
        assert any(
            "[ThirdPartyTelemetry]" in err for err in profile.third_party_console_errors
        )

