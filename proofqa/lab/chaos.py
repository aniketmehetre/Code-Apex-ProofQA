"""Chaos injection knobs and adversarial resilience framework."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from playwright.async_api import BrowserContext, Route


@dataclass
class ChaosConfig:
    """Chaos parameters configurable via WorldSpec or replay harness."""

    latency_ms: int = 0
    offline: bool = False
    aborted_endpoints: list[str] = field(default_factory=list)
    clock_skew_seconds: int = 0
    viewport_width: int = 1280
    viewport_height: int = 720

    def to_dict(self) -> dict[str, Any]:
        return {
            "latency_ms": self.latency_ms,
            "offline": self.offline,
            "aborted_endpoints": self.aborted_endpoints,
            "clock_skew_seconds": self.clock_skew_seconds,
            "viewport_width": self.viewport_width,
            "viewport_height": self.viewport_height,
        }


async def apply_chaos(context: BrowserContext, config: ChaosConfig) -> None:
    """Apply chaos configurations to an active Playwright browser context."""
    if config.offline:
        await context.set_offline(True)

    if config.latency_ms > 0 or config.aborted_endpoints:
        async def route_interceptor(route: Route) -> None:
            url = route.request.url

            # Aborted endpoints
            for abort_path in config.aborted_endpoints:
                if abort_path in url:
                    await route.abort()
                    return

            # Injected latency
            if config.latency_ms > 0:
                await asyncio.sleep(config.latency_ms / 1000.0)

            await route.continue_()

        await context.route("**/*", route_interceptor)
