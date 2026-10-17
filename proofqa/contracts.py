"""ProofQA 2.0: Frozen System Contracts.

Contracts define machine-checkable boundaries, data types, and serialization schemas
for all modules across ProofQA 2.0. These contracts are frozen at Milestone M0.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

contracts_version: str = "1.1"


# ============================================================================
# Action & Perception Contracts
# ============================================================================

class Locator(BaseModel):
    """Multi-strategy element locator prioritized by semantic stability."""
    model_config = ConfigDict(frozen=True)

    role: str | None = None
    name: str | None = None
    label: str | None = None
    testid: str | None = None
    css_fallback: str | None = None


class ActionKind(str, Enum):
    """Enumeration of allowed deterministic browser actions."""
    GOTO = "goto"
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    PRESS = "press"
    WAIT = "wait"


class Action(BaseModel):
    """Deterministic, replayable browser action."""
    model_config = ConfigDict(frozen=True)

    id: str
    kind: ActionKind
    locator: Locator | None = None
    value: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    burst: int = 1

    from pydantic import model_serializer

    @model_serializer(mode="wrap")
    def _serialize(self, handler: Any) -> Any:
        data = handler(self)
        if isinstance(data, dict) and data.get("burst") == 1:
            data.pop("burst", None)
        return data


class StateFingerprint(BaseModel):
    """Normalized page perception state signature."""
    model_config = ConfigDict(frozen=True)

    url_path: str
    aria_hash: str
    simhash: str
    control_count: int


# ============================================================================
# Tape Events (Discriminated Union)
# ============================================================================

class ActionEvent(BaseModel):
    """Recorded action execution event."""
    model_config = ConfigDict(frozen=True)

    type: Literal["action"] = "action"
    action: Action
    timestamp_ms: float = 0.0
    duration_ms: float | None = None


class NetworkEvent(BaseModel):
    """Recorded network request/response pair."""
    model_config = ConfigDict(frozen=True)

    type: Literal["network"] = "network"
    method: str
    url: str
    status: int
    first_party: bool
    request_body_hash: str | None = None
    response_blob_ref: str | None = None
    timestamp_ms: float = 0.0


class ConsoleEvent(BaseModel):
    """Captured browser console output."""
    model_config = ConfigDict(frozen=True)

    type: Literal["console"] = "console"
    level: str
    text: str
    url: str | None = None
    timestamp_ms: float = 0.0


class PageErrorEvent(BaseModel):
    """Uncaught JavaScript runtime error or unhandled promise rejection."""
    model_config = ConfigDict(frozen=True)

    type: Literal["page_error"] = "page_error"
    error_type: str
    message: str
    stack: str | None = None
    timestamp_ms: float = 0.0


class StateEvent(BaseModel):
    """Observed settled page state."""
    model_config = ConfigDict(frozen=True)

    type: Literal["state"] = "state"
    fingerprint: StateFingerprint
    timestamp_ms: float = 0.0


class UiFactEvent(BaseModel):
    """Cross-layer extracted fact comparing UI representation against API truth."""
    model_config = ConfigDict(frozen=True)

    type: Literal["ui_fact"] = "ui_fact"
    label: str
    ui_value: Any
    api_value: Any
    api_ref: str | None = None
    timestamp_ms: float = 0.0


TapeEvent = Annotated[
    Union[
        ActionEvent,
        NetworkEvent,
        ConsoleEvent,
        PageErrorEvent,
        StateEvent,
        UiFactEvent,
    ],
    Field(discriminator="type"),
]


# ============================================================================
# Oracle and Confidence Tiers
# ============================================================================

class OracleClass(str, Enum):
    """Proof strength hierarchy of verification oracles."""
    A = "A"  # Hard signals (5xx, unhandled page errors, console errors)
    B = "B"  # Metamorphic relations (monotonicity, subset, round-trip)
    C = "C"  # Spec claims (quoted description spans)
    D = "D"  # Cross-layer consistency (UI vs network truth)
    E = "E"  # Temporal differential (build diffs on identical trace)
    F = "F"  # Custom / security invariants


class Tier(str, Enum):
    """Grounded confidence tiers assigned to discovered findings."""
    VERIFIED = "VERIFIED"
    VERIFIED_VIOLATION = "VERIFIED_VIOLATION"
    INTERMITTENT = "INTERMITTENT"
    SUSPECTED = "SUSPECTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


# ============================================================================
# Failure Signatures and Message Normalization
# ============================================================================

_UUID_REGEX = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
_TIMESTAMP_REGEX = re.compile(
    r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b"
    r"|\b\d{2}:\d{2}:\d{2}(?:\.\d+)?\b"
)
_HEX_ID_REGEX = re.compile(r"\b0x[0-9a-fA-F]+\b|\b[0-9a-fA-F]{16,64}\b")
_DIGIT_RUNS_REGEX = re.compile(r"\b\d+\b")
_WHITESPACE_REGEX = re.compile(r"\s+")


def normalize_message(msg: str) -> str:
    """Pure normalization function stripping dynamic timestamps, UUIDs, hex IDs, and digits.

    Ensures failure signatures remain stable across runs, seeds, and restarts.
    """
    if not msg:
        return ""

    normalized = _TIMESTAMP_REGEX.sub("<TIMESTAMP>", msg)
    normalized = _UUID_REGEX.sub("<UUID>", normalized)
    normalized = _HEX_ID_REGEX.sub("<HEX>", normalized)
    normalized = _DIGIT_RUNS_REGEX.sub("<NUM>", normalized)
    normalized = _WHITESPACE_REGEX.sub(" ", normalized).strip()
    return normalized


class FailureSignature(BaseModel):
    """Exact signature lock preventing replay slippage to easier bugs."""
    model_config = ConfigDict(frozen=True)

    kind: str
    first_party_endpoint: str | None = None
    status: int | None = None
    error_type: str | None = None
    message_norm: str
    top_frame: str | None = None


# ============================================================================
# Replay, World, and Findings
# ============================================================================

class ReplayOutcomeKind(str, Enum):
    """Three-valued execution outcome."""
    FAIL = "FAIL"              # Target signature observed
    PASS = "PASS"              # Ran fully, target signature not observed
    UNRESOLVED = "UNRESOLVED"  # Prerequisite failed, timeout, or environment error


class ReplayOutcome(BaseModel):
    """Deterministic replay attempt outcome."""
    outcome: ReplayOutcomeKind
    reason: str | None = None
    reproduced: bool = False
    signature: FailureSignature | None = None
    wall_time_ms: float = 0.0
    attempt_log: list[dict[str, Any]] = Field(default_factory=list)


class WorldSpec(BaseModel):
    """Hermetic runtime environment descriptor."""
    model_config = ConfigDict(frozen=True)

    app: str = "shop_twin"
    seed_db: str = "apps/shop_twin/backend/seed.db"
    bugs: list[str] = Field(default_factory=list)
    seed: int = 42
    clock_iso: str = "2026-10-24T09:00:00Z"
    chaos: dict[str, Any] = Field(default_factory=dict)


class Finding(BaseModel):
    """A candidate or verified bug finding."""
    id: str
    oracle_class: OracleClass
    tier: Tier
    signature: FailureSignature
    claim: str
    provenance: str | None = None
    steps: list[Action] = Field(default_factory=list)
    confidence: float = 1.0
    intent_confirmation_needed: bool = False
    observed_rate: str | None = None


# ============================================================================
# Certificate and Verification Verdicts
# ============================================================================

class CertificateManifest(BaseModel):
    """Cryptographically anchored manifest for an issued Bug Certificate."""
    certificate_id: str
    finding_id: str
    created_at: str
    contracts_version: str = contracts_version
    files: dict[str, str] = Field(default_factory=dict)  # relative_path -> sha256
    manifest_hash: str = ""


class VerifyVerdictKind(str, Enum):
    """Independent certificate verification verdict."""
    VALID = "VALID"
    VALID_INTERMITTENT = "VALID_INTERMITTENT"
    INVALID = "INVALID"
    TAMPERED = "TAMPERED"
    UNRESOLVED_ENV = "UNRESOLVED_ENV"


class VerifyVerdict(BaseModel):
    """Output produced by proofqa verify."""
    verdict: VerifyVerdictKind
    reason: str | None = None
    checks: list[dict[str, Any]] = Field(default_factory=list)
    certificate_id: str | None = None
