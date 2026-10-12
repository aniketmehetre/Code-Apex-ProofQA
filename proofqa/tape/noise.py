"""Noise floor profiler capturing pre-existing console and network noise on clean worlds."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from playwright.async_api import ConsoleMessage, Response

from proofqa.browser.harness import BrowserHarness
from proofqa.contracts import normalize_message
from proofqa.world.manager import World


@dataclass
class NoiseProfile:
    """Pre-existing baseline noise observed on a clean application instance."""

    third_party_console_errors: list[str] = field(default_factory=list)
    third_party_network_errors: list[str] = field(default_factory=list)
    first_party_console_errors: list[str] = field(default_factory=list)
    first_party_network_errors: list[str] = field(default_factory=list)

    @property
    def has_first_party_errors(self) -> bool:
        """Returns True if any first-party console or network errors exist in the baseline."""
        return len(self.first_party_console_errors) > 0 or len(self.first_party_network_errors) > 0

    def is_known_noise(self, text: str) -> bool:
        """Checks if a message corresponds to known pre-existing noise."""
        norm = normalize_message(text)
        all_noise = (
            self.third_party_console_errors
            + self.third_party_network_errors
            + self.first_party_console_errors
            + self.first_party_network_errors
        )
        for item in all_noise:
            if normalize_message(item) == norm or norm in normalize_message(item):
                return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "third_party_console_errors": self.third_party_console_errors,
            "third_party_network_errors": self.third_party_network_errors,
            "first_party_console_errors": self.first_party_console_errors,
            "first_party_network_errors": self.first_party_network_errors,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NoiseProfile:
        return cls(
            third_party_console_errors=data.get("third_party_console_errors", []),
            third_party_network_errors=data.get("third_party_network_errors", []),
            first_party_console_errors=data.get("first_party_console_errors", []),
            first_party_network_errors=data.get("first_party_network_errors", []),
        )


async def noise_floor(
    world: World,
    key_pages: list[str] | None = None,
) -> NoiseProfile:
    """Visits key pages twice from a clean world state to build an empirical NoiseProfile.

    Identifies pre-existing third-party failures (e.g. Decoy D02 analytics script)
    so oracles do not falsely flag baseline noise as regressions.
    """
    if key_pages is None:
        key_pages = ["/", "/products", "/about"]

    world_origin = world.url.rstrip("/")
    world_host = urlparse(world_origin).netloc

    third_party_console: set[str] = set()
    third_party_net: set[str] = set()
    first_party_console: set[str] = set()
    first_party_net: set[str] = set()

    harness = BrowserHarness()
    async with harness:
        # Run 2 passes to ensure reproducible baseline detection
        for _ in range(2):
            for path in key_pages:
                full_url = f"{world_origin}{path}"
                context, page = await harness.new_context()

                def on_console(msg: ConsoleMessage) -> None:
                    if msg.type in ("error", "warning"):
                        loc = msg.location or {}
                        msg_url = loc.get("url", "")
                        is_third_party = (
                            "[ThirdPartyTelemetry]" in msg.text
                            or "external-telemetry" in msg.text
                            or (msg_url and world_host not in msg_url)
                        )
                        if is_third_party:
                            third_party_console.add(msg.text)
                        else:
                            first_party_console.add(msg.text)


                def on_response(res: Response) -> None:
                    if res.status >= 400:
                        is_first_party = world_host in res.url
                        entry = f"{res.status} {res.url}"
                        if is_first_party:
                            first_party_net.add(entry)
                        else:
                            third_party_net.add(entry)

                def on_request_failed(req: Any) -> None:
                    req_url = req.url
                    is_first_party = world_host in req_url
                    entry = f"FAILED {req_url}"
                    if is_first_party:
                        first_party_net.add(entry)
                    else:
                        third_party_net.add(entry)

                page.on("console", on_console)
                page.on("response", on_response)
                page.on("requestfailed", on_request_failed)

                try:
                    await page.goto(full_url, wait_until="domcontentloaded", timeout=10000)
                    # Small wait for asynchronous scripts (such as analytics D02) to trigger
                    await asyncio.sleep(0.5)
                except Exception:
                    pass
                finally:
                    await context.close()

    return NoiseProfile(
        third_party_console_errors=sorted(third_party_console),
        third_party_network_errors=sorted(third_party_net),
        first_party_console_errors=sorted(first_party_console),
        first_party_network_errors=sorted(first_party_net),
    )
