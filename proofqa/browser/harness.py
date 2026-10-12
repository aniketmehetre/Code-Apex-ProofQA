"""Async Playwright browser harness with controlled time and deterministic randomness."""

from __future__ import annotations

from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

FIXED_TIME_ISO = "2026-10-24T09:00:00.000Z"

# Deterministic PRNG and fixed Date init script for browser context
DETERMINISTIC_INIT_SCRIPT = """
(function() {
  // 1. Seeded Mulberry32 PRNG for Math.random
  let seed = 42;
  Math.random = function() {
    let t = seed += 0x6D2B79F5;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };

  // 2. Frozen Date override
  const FIXED_TIME = Date.parse("2026-10-24T09:00:00.000Z");
  const OriginalDate = window.Date;
  class FrozenDate extends OriginalDate {
    constructor(...args) {
      if (args.length === 0) {
        super(FIXED_TIME);
      } else {
        super(...args);
      }
    }
    static now() {
      return FIXED_TIME;
    }
  }
  FrozenDate.prototype = OriginalDate.prototype;
  window.Date = FrozenDate;
})();
"""


class BrowserHarness:
    """Manages an isolated Playwright browser session with hermetic perception guarantees."""

    def __init__(
        self,
        headless: bool = True,
        viewport_width: int = 1280,
        viewport_height: int = 800,
        fixed_time_iso: str = FIXED_TIME_ISO,
    ) -> None:
        self.headless = headless
        self.viewport = {"width": viewport_width, "height": viewport_height}
        self.fixed_time_iso = fixed_time_iso
        self._pw: Any = None
        self._browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    async def start(self) -> BrowserHarness:
        """Launch Chromium and configure a pristine context."""
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=self.headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        return self

    async def new_context(self) -> tuple[BrowserContext, Page]:
        """Create a fresh context with fixed viewport and determinism scripts."""
        if not self._browser:
            raise RuntimeError("Browser not started. Call await harness.start() first.")

        self.context = await self._browser.new_context(
            viewport=self.viewport,
            locale="en-US",
            timezone_id="UTC",
        )

        # Inject deterministic clock and Math.random script
        await self.context.add_init_script(DETERMINISTIC_INIT_SCRIPT)

        self.page = await self.context.new_page()
        return self.context, self.page

    async def close(self) -> None:
        """Gracefully release browser resources."""
        if self.context:
            await self.context.close()
            self.context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._pw:
            await self._pw.stop()
            self._pw = None

    async def __aenter__(self) -> BrowserHarness:
        return await self.start()

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()
