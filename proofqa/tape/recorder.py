"""Append-only JSONL tape recorder with blob storage and Playwright telemetry hooks."""

from __future__ import annotations

import asyncio
import hashlib
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.async_api import BrowserContext, ConsoleMessage, Page, Request, Response

from proofqa.contracts import (
    Action,
    ActionEvent,
    ConsoleEvent,
    NetworkEvent,
    PageErrorEvent,
    StateEvent,
    StateFingerprint,
    TapeEvent,
    UiFactEvent,
)


class TapeRecorder:
    """Manages an append-only JSONL tape, response blob storage, and Playwright traces."""

    def __init__(self, output_dir: Path | str, world_origin: str) -> None:
        self.output_dir = Path(output_dir)
        self.world_origin = world_origin.rstrip("/")
        self.world_host = urlparse(self.world_origin).netloc
        self.blob_dir = self.output_dir / "blobs"
        self.traces_dir = self.output_dir / "traces"
        self.screenshots_dir = self.output_dir / "screenshots"
        self.tape_path = self.output_dir / "tape.jsonl"
        self.events: list[TapeEvent] = []
        self._pending_tasks: set[asyncio.Task[Any]] = set()

        self._ensure_directories()

    def _ensure_directories(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.blob_dir.mkdir(parents=True, exist_ok=True)
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    def record_event(self, event: TapeEvent) -> None:
        """Appends a validated TapeEvent to in-memory list and writes to tape.jsonl."""
        self.events.append(event)
        with open(self.tape_path, "a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")

    def record_action(self, action: Action, duration_ms: float | None = None) -> ActionEvent:
        event = ActionEvent(
            action=action,
            timestamp_ms=time.time() * 1000,
            duration_ms=duration_ms,
        )
        self.record_event(event)
        return event

    def record_state(self, fingerprint: StateFingerprint) -> StateEvent:
        event = StateEvent(
            fingerprint=fingerprint,
            timestamp_ms=time.time() * 1000,
        )
        self.record_event(event)
        return event

    def record_ui_fact(
        self,
        label: str,
        ui_value: Any,
        api_value: Any,
        api_ref: str | None = None,
    ) -> UiFactEvent:
        event = UiFactEvent(
            label=label,
            ui_value=ui_value,
            api_value=api_value,
            api_ref=api_ref,
            timestamp_ms=time.time() * 1000,
        )
        self.record_event(event)
        return event

    def attach(self, page: Page) -> None:
        """Hooks into page console, network, and error streams."""

        def on_console(msg: ConsoleMessage) -> None:
            loc = msg.location or {}
            event = ConsoleEvent(
                level=msg.type,
                text=msg.text,
                url=loc.get("url"),
                timestamp_ms=time.time() * 1000,
            )
            self.record_event(event)

        def on_page_error(err: Any) -> None:
            err_str = str(err)
            stack = getattr(err, "stack", None) or err_str
            event = PageErrorEvent(
                error_type=type(err).__name__ if type(err).__name__ != "str" else "PageError",
                message=err_str,
                stack=stack,
                timestamp_ms=time.time() * 1000,
            )
            self.record_event(event)

        def on_response(res: Response) -> None:
            task = asyncio.create_task(self._process_response(res))
            self._pending_tasks.add(task)
            task.add_done_callback(self._pending_tasks.discard)

        def on_request_failed(req: Request) -> None:
            is_first_party = self.world_host in req.url
            event = NetworkEvent(
                method=req.method,
                url=req.url,
                status=0,
                first_party=is_first_party,
                request_body_hash=None,
                response_blob_ref=None,
                timestamp_ms=time.time() * 1000,
            )
            self.record_event(event)

        page.on("console", on_console)
        page.on("pageerror", on_page_error)
        page.on("response", on_response)
        page.on("requestfailed", on_request_failed)

    async def _process_response(self, res: Response) -> None:
        url = res.url
        status = res.status
        method = res.request.method
        is_first_party = self.world_host in url

        req_body_hash: str | None = None
        try:
            post_data = res.request.post_data
            if post_data:
                req_body_hash = hashlib.sha256(post_data.encode("utf-8")).hexdigest()
        except Exception:
            pass

        blob_ref: str | None = None
        try:
            content_type = res.headers.get("content-type", "")
            if "json" in content_type:
                body = await res.body()
                if len(body) <= 256 * 1024:
                    bhash = hashlib.sha256(body).hexdigest()
                    blob_ref = f"{bhash}.json"
                    blob_path = self.blob_dir / blob_ref
                    if not blob_path.exists():
                        blob_path.write_bytes(body)
        except Exception:
            pass

        event = NetworkEvent(
            method=method,
            url=url,
            status=status,
            first_party=is_first_party,
            request_body_hash=req_body_hash,
            response_blob_ref=blob_ref,
            timestamp_ms=time.time() * 1000,
        )
        self.record_event(event)

    async def flush(self) -> None:
        """Awaits any pending async response body reads."""
        if self._pending_tasks:
            await asyncio.gather(*list(self._pending_tasks), return_exceptions=True)

    async def start_tracing(self, context: BrowserContext) -> None:
        """Starts Playwright execution tracing."""
        await context.tracing.start(screenshots=True, snapshots=True, sources=True)

    async def stop_tracing(self, context: BrowserContext, name: str = "trace.zip") -> Path:
        """Stops Playwright execution tracing and exports zip artifact."""
        trace_path = self.traces_dir / name
        await context.tracing.stop(path=str(trace_path))
        return trace_path

    async def save_screenshot(self, page: Page, name: str = "failure.png") -> Path:
        """Saves a screenshot artifact upon failure."""
        screenshot_path = self.screenshots_dir / name
        await page.screenshot(path=str(screenshot_path), full_page=True)
        return screenshot_path
