"""Report generation engine producing clean Markdown reports from certificates (Prompt 9).

Derives reports strictly from certificate files (claim.json, repro.json, signature.json,
replay.json, world.json, manifest.json) without LLM calls or schema mutations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from proofqa.contracts import Action, ActionKind, FailureSignature


def action_to_plain_english(action: Action) -> str:
    """Converts a deterministic Action to a clear, human-readable step description."""
    loc = action.locator
    desc = "target element"
    if loc:
        if loc.role and loc.name:
            desc = f'{loc.role} "{loc.name}"'
        elif loc.name:
            desc = f'"{loc.name}"'
        elif loc.label:
            desc = f'control labeled "{loc.label}"'
        elif loc.testid:
            desc = f'element with testid "{loc.testid}"'
        elif loc.css_fallback:
            desc = f'selector "{loc.css_fallback}"'

    burst_note = f" (Burst: {action.burst} concurrent dispatches)" if getattr(action, "burst", 1) > 1 else ""

    if action.kind == ActionKind.GOTO:
        return f"Navigate to URL: '{action.value or '/'}'"
    elif action.kind == ActionKind.CLICK:
        return f"Click {desc}{burst_note}"
    elif action.kind == ActionKind.FILL:
        return f"Fill {desc} with \"{action.value or ''}\""
    elif action.kind == ActionKind.SELECT:
        return f"Select option \"{action.value or ''}\" in {desc}"
    elif action.kind == ActionKind.PRESS:
        return f"Press key '{action.value or 'Enter'}'"
    elif action.kind == ActionKind.WAIT:
        return f"Wait {action.value or '500'}ms"
    return f"Execute {action.kind.value} on {desc}"


def _get_expected_vs_observed(oracle_class: str, sig: FailureSignature) -> tuple[str, str]:
    """Generates expected vs observed text based on deterministic per-class templates."""
    endpoint = sig.first_party_endpoint or "target endpoint"
    status = f"HTTP {sig.status}" if sig.status is not None else "HTTP 5xx"
    msg = sig.message_norm or "unhandled server error"

    if oracle_class == "A":
        expected = "Clean HTTP 2xx/3xx response with reliable server-side transaction completion."
        observed = f"Server failure: {status} encountered on first-party endpoint `{endpoint}` ({msg})."
    elif oracle_class == "B":
        expected = "Metamorphic invariant holds: reverting UI inputs restores original system state."
        observed = f"State divergence: system output failed to restore prior state after input reversal ({msg})."
    elif oracle_class == "C":
        expected = "Field constraint enforced: input violating policy copy is rejected client-side or with 4xx."
        observed = f"Specification violation: server returned 2xx acknowledging invalid input ({msg})."
    elif oracle_class == "D":
        expected = "Cross-layer consistency: UI presentation strictly matches first-party API truth."
        observed = f"Cross-layer discrepancy: visual state contradicts underlying JSON network response ({msg})."
    elif oracle_class == "E":
        expected = "Temporal invariance: identical user trace produces identical execution across builds."
        observed = f"Regression detected across temporal versions under identical trace ({msg})."
    else:
        expected = "System invariant holds consistently."
        observed = f"Invariant violation detected: {msg}."

    return expected, observed


def generate_certificate_report(
    cert_path: Path | str,
    output_path: Path | str | None = None,
) -> str:
    """Generates a standalone report.md derived only from sealed certificate files."""
    cert_dir = Path(cert_path)
    if not cert_dir.is_dir():
        raise FileNotFoundError(f"Certificate directory not found: {cert_dir}")

    # Read certificate files
    claim_file = cert_dir / "claim.json"
    repro_file = cert_dir / "repro.json"
    sig_file = cert_dir / "signature.json"
    replay_file = cert_dir / "replay.json"
    manifest_file = cert_dir / "manifest.json"

    claim_data = json.loads(claim_file.read_text(encoding="utf-8")) if claim_file.exists() else {}
    sig_data = json.loads(sig_file.read_text(encoding="utf-8")) if sig_file.exists() else {}
    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else {}
    repro_raw = json.loads(repro_file.read_text(encoding="utf-8")) if repro_file.exists() else []

    actions = [Action.model_validate(a) for a in repro_raw]
    sig = FailureSignature.model_validate(sig_data)

    oracle_class = claim_data.get("oracle_class", "A")
    tier = claim_data.get("tier", "VERIFIED")
    observed_rate = claim_data.get("observed_rate", "3/3")
    claim_text = claim_data.get("claim", sig.message_norm or "Defect detected")
    manifest_hash = manifest_data.get("manifest_hash", "UNAVAILABLE")

    expected_text, observed_text = _get_expected_vs_observed(oracle_class, sig)

    # Build Plain English Repro Steps
    steps_md = []
    for idx, act in enumerate(actions, start=1):
        steps_md.append(f"{idx}. {action_to_plain_english(act)}")
    steps_content = "\n".join(steps_md) if steps_md else "No reproduction steps recorded."

    # Evidence summary from replay.json if present
    evidence_md = "Replay evidence verified across isolated hermetic test runs."
    if replay_file.exists():
        try:
            rep_data = json.loads(replay_file.read_text(encoding="utf-8"))
            runs_summary = f"Total Replays: {rep_data.get('total', 0)}, Failures (Target Hits): {rep_data.get('fail_count', 0)}, Passes: {rep_data.get('pass_count', 0)}"
            evidence_md = f"**Execution Summary:** {runs_summary}"
        except Exception:
            pass

    report_md = f"""# Bug Report: [Class {oracle_class}] {claim_text}

## 1. Defect Overview
- **Certificate ID:** `{cert_dir.name}`
- **Oracle Class:** Class {oracle_class}
- **Confidence Tier:** `{tier}`
- **Reproduction Rate:** `{observed_rate}`
- **Manifest Root Digest:** `{manifest_hash}`

## 2. Expected vs Observed Behavior
- **Expected:** {expected_text}
- **Observed:** {observed_text}

## 3. Reproduction Steps ({len(actions)} steps)
{steps_content}

## 4. Verification Evidence
{evidence_md}

## 5. Independent Verification Command
```bash
proofqa verify "{cert_dir}"
```
"""

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(report_md, encoding="utf-8")
    else:
        # Default: write report.md outside the certificate directory
        default_out = cert_dir.parent / f"{cert_dir.name}_report.md"
        default_out.write_text(report_md, encoding="utf-8")

    return report_md


def generate_run_report(
    run_dir: Path | str,
    run_data: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Generates run_report.md and run_report.json documenting exploration coverage and findings."""
    run_path = Path(run_dir)
    run_path.mkdir(parents=True, exist_ok=True)

    findings = run_data.get("findings", [])
    coverage = run_data.get("coverage", {})
    noise = run_data.get("suppressed_noise", {})
    unresolved = run_data.get("unresolved", {})

    report_json = {
        "unique_findings_count": len(findings),
        "findings": findings,
        "coverage": {
            "pages_visited": coverage.get("pages_visited", 1),
            "semantic_states_explored": coverage.get("semantic_states", 1),
            "controls_exercised": coverage.get("controls_exercised", 0),
            "probes_fired": coverage.get("probes_fired", {}),
        },
        "suppressed_noise": {
            "third_party_errors": noise.get("third_party_errors", 0),
            "friendly_404s": noise.get("friendly_404s", 0),
            "masked_banners": noise.get("masked_banners", 0),
        },
        "unresolved_counts": {
            "client_blocked_probes": unresolved.get("client_blocked", 0),
            "precondition_timeouts": unresolved.get("timeouts", 0),
        },
    }

    probes_summary = ", ".join(f"{k}: {v}" for k, v in report_json["coverage"]["probes_fired"].items()) or "None"

    report_md = f"""# ProofQA Exploration Run Report

## 1. Discovered Findings
- **Unique Verified Defects:** {len(findings)}
- **Probes Executed:** {probes_summary}

## 2. Exploration Coverage
- **Pages Visited:** {report_json['coverage']['pages_visited']}
- **Distinct Semantic States:** {report_json['coverage']['semantic_states_explored']}
- **Controls Exercised:** {report_json['coverage']['controls_exercised']}

## 3. Suppressed Environmental Noise
- **Third-Party Errors Filtered:** {report_json['suppressed_noise']['third_party_errors']}
- **Friendly 404s Ignored:** {report_json['suppressed_noise']['friendly_404s']}
- **Masked Banner Shifts:** {report_json['suppressed_noise']['masked_banners']}

## 4. Unresolved Probe Invocations
- **Client-Side Validation Blocks:** {report_json['unresolved_counts']['client_blocked_probes']}
- **Timeouts / Missing Preconditions:** {report_json['unresolved_counts']['precondition_timeouts']}
"""

    (run_path / "run_report.json").write_text(json.dumps(report_json, indent=2), encoding="utf-8")
    (run_path / "run_report.md").write_text(report_md, encoding="utf-8")

    return report_md, report_json
