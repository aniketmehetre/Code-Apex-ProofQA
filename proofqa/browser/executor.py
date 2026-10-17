"""Deterministic action executor trying prioritized locator strategies."""

from __future__ import annotations

import re
from typing import Tuple

from playwright.async_api import Locator as PwLocator
from playwright.async_api import Page

from proofqa.contracts import Action, ActionKind, Locator


async def resolve_element(page: Page, loc: Locator | None, timeout_ms: int = 4000) -> PwLocator | None:
    """Try locator strategies in prioritized order: role+name, label, testid, css_fallback."""
    if not loc:
        return None

    # 1. TestID (unambiguous element selector if present)
    if loc.testid:
        try:
            cand = page.get_by_test_id(loc.testid)
            if await cand.count() > 0 and await cand.first.is_visible():
                return cand.first
        except Exception:
            pass

    # 2. Role + Name (exact first, then case-insensitive substring)
    if loc.role:
        try:
            cand = page.get_by_role(loc.role, name=loc.name)  # type: ignore[arg-type]
            if await cand.count() > 0 and await cand.first.is_visible():
                return cand.first
        except Exception:
            pass
        if loc.name:
            try:
                cand = page.get_by_role(loc.role, name=re.compile(re.escape(loc.name), re.IGNORECASE))  # type: ignore[arg-type]
                if await cand.count() > 0 and await cand.first.is_visible():
                    return cand.first
            except Exception:
                pass

    # 3. Label
    if loc.label:
        try:
            cand = page.get_by_label(loc.label)
            if await cand.count() > 0 and await cand.first.is_visible():
                return cand.first
        except Exception:
            pass

    # 4. CSS Fallback
    if loc.css_fallback:
        try:
            cand = page.locator(loc.css_fallback)
            if await cand.count() > 0 and await cand.first.is_visible():
                return cand.first
        except Exception:
            pass

    # 5. Direct name fallback on buttons/links
    if loc.name:
        try:
            cand = page.locator(f"text={loc.name}")
            if await cand.count() > 0 and await cand.first.is_visible():
                return cand.first
        except Exception:
            pass

    return None


async def execute(page: Page, action: Action, timeout_ms: int = 5000) -> Tuple[bool, str | None]:
    """Execute action with locator fallback. Returns (ok: bool, error_reason: str | None).

    Unexecutable elements return (False, reason), which feeds the UNRESOLVED replay outcome.
    """
    try:
        # Handle GOTO and WAIT without target element
        if action.kind == ActionKind.GOTO:
            if not action.value:
                return False, "not_executable: goto action missing URL value"
            await page.goto(action.value, timeout=timeout_ms, wait_until="load")
            return True, None

        if action.kind == ActionKind.WAIT:
            duration = float(action.value) if action.value else 500.0
            await page.wait_for_timeout(duration)
            return True, None

        # Resolve element
        element = await resolve_element(page, action.locator, timeout_ms=timeout_ms)
        if element is None:
            return False, f"not_executable: element not found for action {action.id} ({action.locator})"

        # Execute action against element
        if action.kind == ActionKind.CLICK:
            await element.click(timeout=timeout_ms)
            return True, None
        elif action.kind == ActionKind.FILL:
            await element.fill(action.value or "", timeout=timeout_ms)
            return True, None
        elif action.kind == ActionKind.SELECT:
            await element.select_option(action.value or "", timeout=timeout_ms)
            return True, None
        elif action.kind == ActionKind.PRESS:
            await element.press(action.value or "Enter", timeout=timeout_ms)
            return True, None
        else:
            return False, f"not_executable: unsupported action kind '{action.kind}'"

    except Exception as exc:
        return False, f"not_executable: {type(exc).__name__}: {exc}"
