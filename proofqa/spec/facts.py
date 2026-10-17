"""Specification Fact Store and deterministic text/attribute extraction (Prompt 4).

Extracts and stores machine-verifiable specification facts from DOM attributes
and page copy using deterministic regular expressions without any LLM dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class SpecFact:
    """A deterministic specification fact extracted from page attributes or text copy."""

    subject: str  # field name, label, or endpoint (e.g. "password", "quantity")
    kind: str  # min_len, max_len, min, max, step, pattern, required, enum
    value: Any
    source: str  # "html_attr" or "copy"
    evidence_text: str
    page: str  # URL path where evidence was found


# Keywords for binding natural language copy to form subjects
SUBJECT_KEYWORDS = [
    "password",
    "quantity",
    "email",
    "address",
    "phone",
    "username",
    "coupon",
    "promo",
    "code",
    "search",
    "name",
]

# Deterministic regex patterns for numerical/length constraints in copy
_COPY_PATTERNS = [
    (
        re.compile(r"at least (\d+) characters", re.IGNORECASE),
        "min_len",
        lambda m: int(m.group(1)),
    ),
    (
        re.compile(r"minimum (\d+) characters", re.IGNORECASE),
        "min_len",
        lambda m: int(m.group(1)),
    ),
    (
        re.compile(r"minimum (\d+)", re.IGNORECASE),
        "min",
        lambda m: int(m.group(1)),
    ),
    (
        re.compile(r"no more than (\d+) characters", re.IGNORECASE),
        "max_len",
        lambda m: int(m.group(1)),
    ),
    (
        re.compile(r"no more than (\d+)", re.IGNORECASE),
        "max",
        lambda m: int(m.group(1)),
    ),
    (
        re.compile(r"between (\d+) and (\d+) characters", re.IGNORECASE),
        "range_len",
        lambda m: (int(m.group(1)), int(m.group(2))),
    ),
    (
        re.compile(r"between (\d+) and (\d+)", re.IGNORECASE),
        "range",
        lambda m: (int(m.group(1)), int(m.group(2))),
    ),
    (
        re.compile(r"(\d+)-(\d+) characters", re.IGNORECASE),
        "range_len",
        lambda m: (int(m.group(1)), int(m.group(2))),
    ),
]


class SpecFactStore:
    """Global repository of specification facts harvested across visited pages."""

    def __init__(self) -> None:
        # subject -> list of SpecFact
        self._facts: dict[str, list[SpecFact]] = {}

    def add_fact(self, fact: SpecFact) -> None:
        """Stores a fact if not already present."""
        subj = fact.subject.strip().lower()
        if subj not in self._facts:
            self._facts[subj] = []

        # Avoid exact duplicates
        for existing in self._facts[subj]:
            if (
                existing.kind == fact.kind
                and existing.value == fact.value
                and existing.source == fact.source
            ):
                return
        self._facts[subj].append(fact)

    def get_facts(self, subject: str) -> list[SpecFact]:
        """Returns all facts associated with a subject."""
        subj = subject.strip().lower()
        matched: list[SpecFact] = []
        for s, flist in self._facts.items():
            if s == subj or s in subj or subj in s:
                matched.extend(flist)
        return matched

    def get_fact_value(self, subject: str, kind: str) -> Any | None:
        """Returns the most restrictive or explicit value for a given subject and kind."""
        facts = [f for f in self.get_facts(subject) if f.kind == kind]
        if not facts:
            return None
        # Return first recorded fact value
        return facts[0].value

    def extract_from_html_attributes(
        self,
        element_attrs: dict[str, Any],
        subject: str,
        page: str = "/",
    ) -> list[SpecFact]:
        """Extracts facts from standard HTML form attributes."""
        extracted: list[SpecFact] = []
        subj = subject.strip().lower()

        if "minlength" in element_attrs and element_attrs["minlength"] is not None:
            try:
                val = int(element_attrs["minlength"])
                fact = SpecFact(
                    subject=subj,
                    kind="min_len",
                    value=val,
                    source="html_attr",
                    evidence_text=f"minlength='{val}'",
                    page=page,
                )
                self.add_fact(fact)
                extracted.append(fact)
            except (ValueError, TypeError):
                pass

        if "maxlength" in element_attrs and element_attrs["maxlength"] is not None:
            try:
                val = int(element_attrs["maxlength"])
                fact = SpecFact(
                    subject=subj,
                    kind="max_len",
                    value=val,
                    source="html_attr",
                    evidence_text=f"maxlength='{val}'",
                    page=page,
                )
                self.add_fact(fact)
                extracted.append(fact)
            except (ValueError, TypeError):
                pass

        if "min" in element_attrs and element_attrs["min"] is not None:
            try:
                val = float(element_attrs["min"])
                fact = SpecFact(
                    subject=subj,
                    kind="min",
                    value=val,
                    source="html_attr",
                    evidence_text=f"min='{val}'",
                    page=page,
                )
                self.add_fact(fact)
                extracted.append(fact)
            except (ValueError, TypeError):
                pass

        if "max" in element_attrs and element_attrs["max"] is not None:
            try:
                val = float(element_attrs["max"])
                fact = SpecFact(
                    subject=subj,
                    kind="max",
                    value=val,
                    source="html_attr",
                    evidence_text=f"max='{val}'",
                    page=page,
                )
                self.add_fact(fact)
                extracted.append(fact)
            except (ValueError, TypeError):
                pass

        if element_attrs.get("required"):
            fact = SpecFact(
                subject=subj,
                kind="required",
                value=True,
                source="html_attr",
                evidence_text="required",
                page=page,
            )
            self.add_fact(fact)
            extracted.append(fact)

        if "pattern" in element_attrs and element_attrs["pattern"]:
            pat = str(element_attrs["pattern"])
            fact = SpecFact(
                subject=subj,
                kind="pattern",
                value=pat,
                source="html_attr",
                evidence_text=f"pattern='{pat}'",
                page=page,
            )
            self.add_fact(fact)
            extracted.append(fact)

        return extracted

    def extract_from_page_copy(
        self,
        text: str,
        page: str = "/",
    ) -> list[SpecFact]:
        """Extracts facts from page copy using deterministic regex and keyword binding."""
        extracted: list[SpecFact] = []
        if not text:
            return extracted

        # Split text into sentences or lines
        sentences = re.split(r"[.\n;]", text)
        for sentence in sentences:
            sentence_clean = sentence.strip()
            if not sentence_clean:
                continue

            # Identify matching subject keywords
            sentence_lower = sentence_clean.lower()
            matching_subjects = [kw for kw in SUBJECT_KEYWORDS if kw in sentence_lower]
            if not matching_subjects:
                continue

            for pattern, kind, extractor in _COPY_PATTERNS:
                match = pattern.search(sentence_clean)
                if match:
                    val = extractor(match)
                    for subj in matching_subjects:
                        if kind == "range_len":
                            min_val, max_val = val
                            f_min = SpecFact(
                                subject=subj,
                                kind="min_len",
                                value=min_val,
                                source="copy",
                                evidence_text=sentence_clean,
                                page=page,
                            )
                            f_max = SpecFact(
                                subject=subj,
                                kind="max_len",
                                value=max_val,
                                source="copy",
                                evidence_text=sentence_clean,
                                page=page,
                            )
                            self.add_fact(f_min)
                            self.add_fact(f_max)
                            extracted.extend([f_min, f_max])
                        elif kind == "range":
                            min_val, max_val = val
                            f_min = SpecFact(
                                subject=subj,
                                kind="min",
                                value=min_val,
                                source="copy",
                                evidence_text=sentence_clean,
                                page=page,
                            )
                            f_max = SpecFact(
                                subject=subj,
                                kind="max",
                                value=max_val,
                                source="copy",
                                evidence_text=sentence_clean,
                                page=page,
                            )
                            self.add_fact(f_min)
                            self.add_fact(f_max)
                            extracted.extend([f_min, f_max])
                        else:
                            f = SpecFact(
                                subject=subj,
                                kind=kind,
                                value=val,
                                source="copy",
                                evidence_text=sentence_clean,
                                page=page,
                            )
                            self.add_fact(f)
                            extracted.append(f)

        return extracted
