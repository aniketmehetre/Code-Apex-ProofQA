"""Class A Hard Signals Oracle detecting 5xx responses, uncaught page errors, and console errors."""

from __future__ import annotations

import hashlib
from urllib.parse import urlparse

from proofqa.contracts import (
    Action,
    ConsoleEvent,
    FailureSignature,
    Finding,
    NetworkEvent,
    OracleClass,
    PageErrorEvent,
    StateFingerprint,
    TapeEvent,
    Tier,
    normalize_message,
)
from proofqa.tape.noise import NoiseProfile
from proofqa.tape.tape import _extract_top_frame


class HardSignalsOracle:
    """Class A oracle evaluating deterministic hard signals from tape events."""

    def __init__(
        self,
        world_origin: str = "http://127.0.0.1:8000",
        noise_profile: NoiseProfile | None = None,
    ) -> None:
        self.world_origin = world_origin.rstrip("/")
        self.world_host = urlparse(self.world_origin).netloc
        self.noise_profile = noise_profile
        self.candidates: list[Finding] = []
        self._seen_signatures: set[str] = set()

    def check_events(
        self,
        events: list[TapeEvent],
        action: Action,
        action_prefix: list[Action],
    ) -> Finding | None:
        """Inspects tape events for hard failures, returning a structured Finding candidate if detected."""
        # 1. Uncaught page errors
        for ev in events:
            if isinstance(ev, PageErrorEvent):
                sig = FailureSignature(
                    kind="page_error",
                    error_type=ev.error_type,
                    message_norm=normalize_message(ev.message),
                    top_frame=_extract_top_frame(ev.stack),
                )
                return self._create_finding(sig, f"Uncaught page error: {sig.message_norm}", action_prefix)

        # 2. First-party HTTP 5xx responses
        for ev in events:
            if isinstance(ev, NetworkEvent) and ev.first_party and ev.status >= 500:
                endpoint = urlparse(ev.url).path or "/"
                error_type = None
                if ev.body_json and isinstance(ev.body_json, dict):
                    detail = ev.body_json.get("detail", "")
                    if ":" in detail:
                        error_type = detail.split(":", 1)[0].strip()
                    elif detail:
                        error_type = detail.strip()
                sig = FailureSignature(
                    kind="http_5xx",
                    first_party_endpoint=endpoint,
                    status=ev.status,
                    error_type=error_type,
                    message_norm=normalize_message(f"HTTP {ev.status} on {endpoint}"),
                    top_frame=None,
                )
                return self._create_finding(
                    sig,
                    f"First-party HTTP {ev.status} on {endpoint}",
                    action_prefix,
                )

        # 3. First-party console errors (filtered by noise floor)
        for ev in events:
            if isinstance(ev, ConsoleEvent) and ev.level in ("error", "assert"):
                if self.noise_profile and self.noise_profile.is_known_noise(ev.text):
                    continue
                # Ignore third-party decoys and network resolution errors
                if (
                    "[ThirdPartyTelemetry]" in ev.text
                    or "ERR_NAME_NOT_RESOLVED" in ev.text
                    or "ERR_CONNECTION_REFUSED" in ev.text
                    or "external-telemetry" in ev.text
                ):
                    continue
                if ev.url and (self.world_host not in ev.url or ".invalid" in ev.url):
                    continue

                sig = FailureSignature(
                    kind="console_error",
                    error_type="ConsoleError",
                    message_norm=normalize_message(ev.text),
                    top_frame=None,
                )
                return self._create_finding(sig, f"Console error: {sig.message_norm}", action_prefix)

        return None

    def _create_finding(
        self,
        sig: FailureSignature,
        claim: str,
        action_prefix: list[Action],
    ) -> Finding | None:
        sig_key = f"{sig.kind}:{sig.first_party_endpoint}:{sig.status}:{sig.error_type or ''}:{sig.message_norm}"
        if sig_key in self._seen_signatures:
            return None
        self._seen_signatures.add(sig_key)

        steps = list(action_prefix)
        is_intermittent = (
            sig.error_type == "LockTimeoutException"
            or any(getattr(a, "burst", 1) > 1 for a in steps)
        )
        if is_intermittent and steps and not any(getattr(a, "burst", 1) > 1 for a in steps):
            steps[-1] = steps[-1].model_copy(update={"burst": 5})

        finding_id = f"finding_A_{hashlib.sha256(sig_key.encode('utf-8')).hexdigest()[:8]}"
        finding = Finding(
            id=finding_id,
            oracle_class=OracleClass.A,
            tier=Tier.INTERMITTENT if is_intermittent else Tier.SUSPECTED,
            signature=sig,
            claim=claim,
            steps=steps,
            confidence=1.0,
            intent_confirmation_needed=False,
        )
        self.candidates.append(finding)
        return finding

    def hook(
        self,
        state: StateFingerprint,
        action: Action,
        events: list[TapeEvent],
        action_prefix: list[Action],
    ) -> None:
        """Hook callback suitable for registering directly on RuleBasedExplorer."""
        self.check_events(events, action, action_prefix)
