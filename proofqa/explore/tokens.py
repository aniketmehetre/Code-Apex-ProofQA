"""TokenPool: harvesting coupon, promo, and authentication tokens from page data (Prompt 4)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from proofqa.contracts import Action

TOKEN_REGEX = re.compile(r"^[A-Za-z0-9_-]{3,24}$")
_PROMO_KEYWORDS = ["code", "promo", "coupon", "voucher", "discount"]


class TokenPool:
    """Harvests candidate string tokens from page text, placeholders, API responses, and fixtures.

    Tokens are used ONLY as fill values, never as locators or URLs, and never sent to an LLM.
    """

    def __init__(self, fixtures_path: Path | str | None = None) -> None:
        self.tokens: set[str] = set()
        self.fixtures: dict[str, Any] = {}
        if fixtures_path:
            self.load_fixtures(fixtures_path)

    def load_fixtures(self, fixtures_path: Path | str) -> None:
        """Loads optional operator fixtures YAML."""
        p = Path(fixtures_path)
        if not p.exists():
            return
        import yaml  # type: ignore

        try:
            content = yaml.safe_load(p.read_text(encoding="utf-8"))
            if isinstance(content, dict):
                self.fixtures = content
                for code in content.get("promo_codes", []):
                    if TOKEN_REGEX.match(str(code)):
                        self.tokens.add(str(code))
        except Exception:
            pass

    def harvest_from_text(self, text: str) -> list[str]:
        """Harvests tokens from DOM text appearing near promo keywords."""
        if not text:
            return []
        found: list[str] = []
        words = text.split()
        for i, word in enumerate(words):
            w_clean = word.strip(":,.;!?\"'()[]{}").lower()
            if any(kw in w_clean for kw in _PROMO_KEYWORDS):
                # Inspect nearby candidate tokens (window of 3 words before and after)
                start = max(0, i - 3)
                end = min(len(words), i + 4)
                for cand_word in words[start:end]:
                    cand = cand_word.strip(":,.;!?\"'()[]{}")
                    if cand and TOKEN_REGEX.match(cand) and cand.lower() not in _PROMO_KEYWORDS:
                        if cand not in self.tokens:
                            self.tokens.add(cand)
                            found.append(cand)
        return found

    def harvest_from_placeholders(self, candidates: list[Action]) -> list[str]:
        """Harvests tokens embedded in input placeholders or labels."""
        found: list[str] = []
        for act in candidates:
            loc = act.locator
            if not loc:
                continue
            for val in [loc.label, loc.name]:
                if val:
                    for part in val.split():
                        part_clean = part.strip(":,.;!?\"'()[]{}")
                        if TOKEN_REGEX.match(part_clean) and part_clean.lower() not in _PROMO_KEYWORDS:
                            if part_clean not in self.tokens:
                                self.tokens.add(part_clean)
                                found.append(part_clean)
        return found

    def harvest_from_api_response(self, data: Any) -> list[str]:
        """Recursively harvests tokens from JSON API response dictionaries."""
        found: list[str] = []
        if isinstance(data, dict):
            for k, v in data.items():
                if any(kw in k.lower() for kw in _PROMO_KEYWORDS) and isinstance(v, str):
                    v_clean = v.strip()
                    if TOKEN_REGEX.match(v_clean) and v_clean not in self.tokens:
                        self.tokens.add(v_clean)
                        found.append(v_clean)
                found.extend(self.harvest_from_api_response(v))
        elif isinstance(data, list):
            for item in data:
                found.extend(self.harvest_from_api_response(item))
        return found

    def get_tokens(self) -> list[str]:
        """Returns deterministic sorted list of all active tokens."""
        return sorted(self.tokens)
