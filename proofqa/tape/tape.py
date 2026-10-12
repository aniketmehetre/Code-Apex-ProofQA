"""Tape container, loader, and failure signature derivation."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from pydantic import TypeAdapter

from proofqa.contracts import (
    Action,
    ActionEvent,
    ConsoleEvent,
    FailureSignature,
    NetworkEvent,
    PageErrorEvent,
    TapeEvent,
    normalize_message,
)
from proofqa.tape.noise import NoiseProfile


def _extract_top_frame(stack: str | None) -> str | None:
    """Extracts normalized top stack frame identifier from error traceback."""
    if not stack:
        return None
    lines = [line.strip() for line in stack.splitlines() if line.strip()]
    for line in lines:
        if line.startswith("at ") or "http://" in line or "https://" in line or ".js:" in line:
            # Strip query strings and digit line/column numbers for stability
            cleaned = re.sub(r":\d+(?::\d+)?", "", line)
            return normalize_message(cleaned)
    if lines:
        return normalize_message(lines[0])
    return None


class Tape:
    """In-memory representation of an append-only JSONL execution tape."""

    def __init__(
        self,
        events: list[TapeEvent],
        tape_path: Path | None = None,
        blob_dir: Path | None = None,
    ) -> None:
        self.events = events
        self.tape_path = Path(tape_path) if tape_path else None
        self.blob_dir = Path(blob_dir) if blob_dir else None

    @classmethod
    def load(cls, tape_path: Path | str) -> Tape:
        """Loads and validates a tape from an existing JSONL file."""
        path = Path(tape_path)
        adapter: TypeAdapter[TapeEvent] = TypeAdapter(TapeEvent)
        events: list[TapeEvent] = []

        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line_str = line.strip()
                    if line_str:
                        events.append(adapter.validate_json(line_str))

        blob_dir = path.parent / "blobs"
        return cls(
            events=events,
            tape_path=path,
            blob_dir=blob_dir if blob_dir.exists() else None,
        )

    def actions(self) -> list[Action]:
        """Returns ordered list of executed actions."""
        return [e.action for e in self.events if isinstance(e, ActionEvent)]


def signature_from_events(
    events: list[TapeEvent],
    noise_profile: NoiseProfile | None = None,
) -> FailureSignature | None:
    """Derives deterministic FailureSignature from tape event sequence.

    Evaluates errors in prioritized order:
    1. PageErrorEvent (unhandled exception in page)
    2. First-party NetworkEvent with HTTP status >= 500
    3. First-party ConsoleEvent with level 'error' not present in noise floor.
    """
    # 1. Uncaught page errors
    for ev in events:
        if isinstance(ev, PageErrorEvent):
            return FailureSignature(
                kind="page_error",
                error_type=ev.error_type,
                message_norm=normalize_message(ev.message),
                top_frame=_extract_top_frame(ev.stack),
            )

    # 2. First-party 5xx responses
    for ev in events:
        if isinstance(ev, NetworkEvent) and ev.first_party and ev.status >= 500:
            parsed_url = urlparse(ev.url)
            path = parsed_url.path or "/"
            return FailureSignature(
                kind="http_5xx",
                first_party_endpoint=path,
                status=ev.status,
                message_norm=normalize_message(f"HTTP {ev.status} on {path}"),
                top_frame=None,
            )

    # 3. Console errors
    for ev in events:
        if isinstance(ev, ConsoleEvent) and ev.level in ("error", "assert"):
            if noise_profile and noise_profile.is_known_noise(ev.text):
                continue
            # If D02 or third-party net failure, ignore as non-first-party noise
            if (
                "[ThirdPartyTelemetry]" in ev.text
                or "ERR_NAME_NOT_RESOLVED" in ev.text
                or "ERR_CONNECTION_REFUSED" in ev.text
                or "ERR_INTERNET_DISCONNECTED" in ev.text
                or "external-telemetry" in ev.text
            ):
                continue
            if ev.url and ("external-telemetry" in ev.url or ".invalid" in ev.url):
                continue
            return FailureSignature(
                kind="console_error",
                error_type="ConsoleError",
                message_norm=normalize_message(ev.text),
                top_frame=None,
            )

    return None
