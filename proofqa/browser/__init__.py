"""ProofQA Browser Harness and Perception Package."""

from proofqa.browser.executor import execute, resolve_element
from proofqa.browser.harness import BrowserHarness
from proofqa.browser.perception import (
    compute_simhash,
    detect_volatile_regions,
    extract_candidate_actions,
    get_page_fingerprint,
    normalize_aria_text,
)

__all__ = [
    "BrowserHarness",
    "execute",
    "resolve_element",
    "get_page_fingerprint",
    "detect_volatile_regions",
    "extract_candidate_actions",
    "normalize_aria_text",
    "compute_simhash",
]
