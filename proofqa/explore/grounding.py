"""Deterministic action grounding choke point and input sanitization.

All actions proposed by probes or LLM proposers must pass through ground_action()
before execution. Ungrounded actions targeting non-existent elements are dropped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from proofqa.contracts import Action, ActionKind, Locator

# Control characters ASCII 0-31 except \t (\x09), \n (\x0a), \r (\x0d)
_CONTROL_CHARS_REGEX = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MAX_FILL_VALUE_LENGTH = 10000


@dataclass
class GroundingTelemetry:
    """Telemetry tracking grounded vs dropped actions."""

    grounded_count: int = 0
    dropped_count: int = 0
    sanitized_count: int = 0
    dropped_reasons: list[str] = field(default_factory=list)


TELEMETRY = GroundingTelemetry()


def sanitize_input_value(value: str | None) -> str | None:
    """Sanitizes form input values: enforces length cap and strips dangerous control characters."""
    if value is None:
        return None
    # 1. Enforce length cap
    sanitized = value[:MAX_FILL_VALUE_LENGTH]
    # 2. Strip non-printable control characters
    sanitized = _CONTROL_CHARS_REGEX.sub("", sanitized)
    if sanitized != value:
        TELEMETRY.sanitized_count += 1
    return sanitized


def _locator_matches(cand_loc: Locator | None, target_loc: Locator | None) -> bool:
    """Evaluates whether candidate action locator matches grounded control locator."""
    if not cand_loc or not target_loc:
        return False

    # Exact locator equality
    if cand_loc == target_loc:
        return True

    # Match by data-testid if present
    if cand_loc.testid and target_loc.testid:
        return cand_loc.testid == target_loc.testid

    # Match by CSS fallback selector
    if cand_loc.css_fallback and target_loc.css_fallback and cand_loc.css_fallback == target_loc.css_fallback:
        return True

    # Match by role and name / label (ARIA accessible name)
    if cand_loc.role and target_loc.role and cand_loc.role == target_loc.role:
        cand_names = [n.strip().lower() for n in (cand_loc.name, cand_loc.label) if n]
        target_names = [n.strip().lower() for n in (target_loc.name, target_loc.label) if n]
        if not cand_names or not target_names:
            return True
        # 1. Exact string match
        for cn in cand_names:
            for tn in target_names:
                if cn == tn:
                    return True
        # 2. Word-boundary match: require strong overlap (at least 50% of candidate words or >= 2 words)
        cand_words = {w for n in cand_names for w in re.findall(r'[a-z0-9]+', n) if len(w) > 1 and w not in {"the", "a", "an", "to", "in", "on", "of", "by", "for"}}
        target_words = {w for n in target_names for w in re.findall(r'[a-z0-9]+', n) if len(w) > 1 and w not in {"the", "a", "an", "to", "in", "on", "of", "by", "for"}}
        common = cand_words & target_words
        if common and (len(common) == len(cand_words) or len(common) >= 2 or len(common) / max(len(cand_words), 1) >= 0.5):
            return True

    return False


def ground_action(
    action: Action,
    grounded_controls: list[Action],
) -> Action | None:
    """Choke point validating action against grounded page controls.

    - GOTO and WAIT actions without locators pass through automatically.
    - Interactive actions (CLICK, FILL, SELECT, PRESS) must match a grounded control.
    - Fill values are sanitized.
    - Ungrounded actions are dropped and counted.
    """
    # 1. Passive / navigation actions do not require locator grounding
    if action.kind in (ActionKind.GOTO, ActionKind.WAIT):
        sanitized_val = sanitize_input_value(action.value)
        TELEMETRY.grounded_count += 1
        return Action(
            id=action.id,
            kind=action.kind,
            locator=action.locator,
            value=sanitized_val,
            params=action.params,
            burst=getattr(action, "burst", 1),
        )

    # 2. Match interactive actions against grounded controls
    matched_control: Action | None = None
    target_testid = action.locator.testid if action.locator else None

    # Pass 1: exact testid match if action specified testid
    if target_testid:
        for control in grounded_controls:
            if (control.kind == action.kind or (action.kind == ActionKind.PRESS and control.kind == ActionKind.CLICK)) and control.locator:
                if control.locator.testid == target_testid:
                    matched_control = control
                    break

    # Pass 2: exact name or label match
    if not matched_control and action.locator:
        cand_exact = [n.strip().lower() for n in (action.locator.name, action.locator.label) if n]
        for control in grounded_controls:
            if (control.kind == action.kind or (action.kind == ActionKind.PRESS and control.kind == ActionKind.CLICK)) and control.locator:
                ctrl_exact = [n.strip().lower() for n in (control.locator.name, control.locator.label) if n]
                if any(ce in ctrl_exact for ce in cand_exact):
                    if not action.locator.role or not control.locator.role or action.locator.role == control.locator.role:
                        matched_control = control
                        break

    # Pass 3: generic locator matching with word overlap
    if not matched_control:
        for control in grounded_controls:
            if control.kind == action.kind or (action.kind == ActionKind.PRESS and control.kind == ActionKind.CLICK):
                if control.id == action.id or _locator_matches(action.locator, control.locator):
                    matched_control = control
                    break

    if not matched_control:
        TELEMETRY.dropped_count += 1
        reason = f"Ungrounded action {action.kind.value} targeting locator {action.locator}"
        TELEMETRY.dropped_reasons.append(reason)
        return None

    # 3. Use grounded locator and apply input value sanitization
    sanitized_val = sanitize_input_value(action.value)
    TELEMETRY.grounded_count += 1

    out_locator = matched_control.locator
    if action.locator and not action.locator.testid and (action.locator.role or action.locator.name or action.locator.label):
        out_locator = action.locator

    return Action(
        id=action.id,
        kind=action.kind,
        locator=out_locator,
        value=sanitized_val,
        params=action.params or matched_control.params,
        burst=getattr(action, "burst", 1),
    )
