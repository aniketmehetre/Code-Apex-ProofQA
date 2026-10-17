"""Perception, ARIA normalization, simhashing, and candidate action extraction."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse

from playwright.async_api import Page

from proofqa.contracts import Action, ActionKind, Locator, StateFingerprint

_WHITESPACE_RE = re.compile(r"\s+")


def compute_simhash(text: str) -> str:
    """Compute 64-bit locality-sensitive simhash of input text."""
    tokens = _WHITESPACE_RE.split(text.lower().strip())
    tokens = [t for t in tokens if len(t) > 1]
    if not tokens:
        return "0" * 16

    v = [0] * 64
    for token in tokens:
        token_hash = int(hashlib.md5(token.encode("utf-8")).hexdigest()[:16], 16)
        for i in range(64):
            bit = (token_hash >> i) & 1
            v[i] += 1 if bit else -1

    fingerprint = 0
    for i in range(64):
        if v[i] > 0:
            fingerprint |= 1 << i

    return f"{fingerprint:016x}"


def detect_volatile_regions(aria1: str, aria2: str) -> set[str]:
    """Compare two fresh page loads and extract lines that differ (e.g. rotating banners)."""
    lines1 = set(line.strip() for line in aria1.splitlines() if line.strip())
    lines2 = set(line.strip() for line in aria2.splitlines() if line.strip())
    diff = lines1.symmetric_difference(lines2)
    return diff


def normalize_aria_text(aria_text: str, volatile_mask: set[str] | None = None) -> str:
    """Normalize accessibility tree text, masking volatile/rotating regions."""
    lines = []
    mask = volatile_mask or set()
    for line in aria_text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        # If line contains any masked phrase, replace with <VOLATILE>
        is_volatile = any(v in cleaned for v in mask) if mask else False
        if is_volatile:
            lines.append("<VOLATILE>")
        else:
            lines.append(cleaned)
    return "\n".join(lines)


async def get_page_fingerprint(
    page: Page,
    volatile_mask: set[str] | None = None,
) -> StateFingerprint:
    """Extract normalized StateFingerprint from page URL and ARIA tree."""
    parsed = urlparse(page.url)
    url_path = parsed.path or "/"

    # Extract ARIA snapshot from modern Playwright
    try:
        raw_text = await page.aria_snapshot()
    except Exception:
        raw_text = await page.inner_text("body")

    normalized_text = normalize_aria_text(raw_text, volatile_mask)
    aria_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()[:16]
    simhash_val = compute_simhash(normalized_text)

    # Count interactive controls
    control_elements = await page.query_selector_all("button, a, input, select, textarea")
    control_count = len(control_elements)

    return StateFingerprint(
        url_path=url_path,
        aria_hash=f"aria:{aria_hash}",
        simhash=f"sim:{simhash_val}",
        control_count=control_count,
    )


async def extract_candidate_actions(
    page: Page,
    origin: str | None = None,
) -> list[Action]:
    """Extract interactive candidate actions filtered by same-origin safety policy."""
    actions: list[Action] = []
    base_origin = origin or f"{urlparse(page.url).scheme}://{urlparse(page.url).netloc}"

    # 1. Buttons and clickable elements
    buttons = await page.query_selector_all("button:visible, [role='button']:visible")
    for btn in buttons:
        name = (await btn.text_content() or "").strip()
        testid = await btn.get_attribute("data-testid")
        aria_label = await btn.get_attribute("aria-label")
        label = aria_label or name
        btn_id = hashlib.sha256(f"button:{label}:{testid}".encode("utf-8")).hexdigest()[:8]

        actions.append(
            Action(
                id=f"act_click_{btn_id}",
                kind=ActionKind.CLICK,
                locator=Locator(
                    role="button",
                    name=name if name else None,
                    label=aria_label or name,
                    testid=testid,
                ),
            )
        )

    # 1b. Product Headings (opens product detail modal)
    headings = await page.query_selector_all("h3.product-title:visible")
    for h in headings:
        name = (await h.text_content() or "").strip()
        h_id = hashlib.sha256(f"heading:{name}".encode("utf-8")).hexdigest()[:8]
        actions.append(
            Action(
                id=f"act_click_{h_id}",
                kind=ActionKind.CLICK,
                locator=Locator(
                    role="heading",
                    name=name,
                    label=name,
                    css_fallback=".product-title",
                ),
            )
        )

    # 2. Links (Same-origin only)
    links = await page.query_selector_all("a:visible")
    for link in links:
        href = (await link.get_attribute("href") or "").strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
        if href.startswith("http://") or href.startswith("https://"):
            link_origin = f"{urlparse(href).scheme}://{urlparse(href).netloc}"
            if link_origin != base_origin:
                continue  # Deny off-origin link

        text = (await link.text_content() or "").strip()
        link_id = hashlib.sha256(f"link:{text}:{href}".encode("utf-8")).hexdigest()[:8]
        actions.append(
            Action(
                id=f"act_goto_{link_id}",
                kind=ActionKind.GOTO,
                value=href,
                locator=Locator(role="link", name=text if text else None),
            )
        )

    # 3. Inputs
    inputs = await page.query_selector_all("input:visible, textarea:visible")
    for inp in inputs:
        inp_type = (await inp.get_attribute("type") or "text").lower()
        if inp_type in {"submit", "button", "hidden"}:
            continue
        aria_label = await inp.get_attribute("aria-label")
        placeholder = await inp.get_attribute("placeholder")
        inp_id_attr = await inp.get_attribute("id")
        inp_name = await inp.get_attribute("name")
        testid = await inp.get_attribute("data-testid")
        label = aria_label or placeholder or inp_name or inp_id_attr or "input"
        act_id = hashlib.sha256(f"fill:{label}:{inp_id_attr}:{testid}".encode("utf-8")).hexdigest()[:8]

        role = "spinbutton" if inp_type == "number" else ("searchbox" if inp_type == "search" else "textbox")
        actions.append(
            Action(
                id=f"act_fill_{act_id}",
                kind=ActionKind.FILL,
                locator=Locator(
                    role=role,
                    name=inp_name or aria_label or placeholder,
                    label=aria_label or placeholder or inp_name,
                    testid=testid,
                    css_fallback=f"#{inp_id_attr}" if inp_id_attr else None,
                ),
                value="test_input",
            )
        )

    # 4. Select dropdowns
    selects = await page.query_selector_all("select:visible")
    for sel in selects:
        aria_label = await sel.get_attribute("aria-label")
        sel_id_attr = await sel.get_attribute("id")
        sel_name = await sel.get_attribute("name")
        testid = await sel.get_attribute("data-testid")
        label = aria_label or sel_name or sel_id_attr or "select"
        act_id = hashlib.sha256(f"select:{label}:{sel_id_attr}:{testid}".encode("utf-8")).hexdigest()[:8]
        actions.append(
            Action(
                id=f"act_select_{act_id}",
                kind=ActionKind.SELECT,
                locator=Locator(
                    role="combobox",
                    name=sel_name or aria_label,
                    label=aria_label or sel_name,
                    testid=testid,
                    css_fallback=f"#{sel_id_attr}" if sel_id_attr else None,
                ),
                value="Electronics",
            )
        )

    return actions
