"""Independent certificate verification engine obeying Architecture Rule 3.

Checks:
1. Cryptographic manifest integrity (SHA-256 for all certificate files).
2. World environment rebuild from world.json.
3. 3x deterministic replay via independent Playwright executor.
4. Grounded signature matching.
Verdicts:
- VALID: Signature matched consistently.
- INVALID: Replay executed but failure signature did not reproduce.
- TAMPERED: Any certificate file failed hash validation.
- UNRESOLVED_ENV: Environment could not be instantiated or executed.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

from proofqa.contracts import (
    Action,
    ActionKind,
    CertificateManifest,
    FailureSignature,
    VerifyVerdict,
    VerifyVerdictKind,
    WorldSpec,
    normalize_message,
)
from proofqa.world.manager import World


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def signatures_match(target: FailureSignature, observed: FailureSignature) -> bool:
    if target.kind != observed.kind:
        return False
    if target.status is not None and observed.status is not None and target.status != observed.status:
        return False
    if target.first_party_endpoint and observed.first_party_endpoint:
        if target.first_party_endpoint != observed.first_party_endpoint:
            return False
    if target.error_type and observed.error_type:
        if target.error_type != observed.error_type:
            return False
    if target.message_norm and observed.message_norm:
        if target.message_norm != observed.message_norm:
            return False
    return True


async def verify_certificate(
    cert_path: Path | str,
    use_docker: bool = False,
    replay_count: int = 3,
    verbose: bool = True,
) -> VerifyVerdict:
    """Independently verify a certificate directory."""
    path = Path(cert_path)
    if not path.is_dir():
        if verbose:
            print(f"CHECK 1: Directory {path} does not exist.")
            print("VERDICT: UNRESOLVED_ENV")
        return VerifyVerdict(verdict=VerifyVerdictKind.UNRESOLVED_ENV, reason=f"Directory {path} does not exist")

    # --- Step 1: Manifest Integrity Check ---
    manifest_file = path / "manifest.json"
    if not manifest_file.exists():
        if verbose:
            print("CHECK 1: manifest.json missing -> TAMPERED")
            print("VERDICT: TAMPERED")
        return VerifyVerdict(verdict=VerifyVerdictKind.TAMPERED, reason="manifest.json missing")

    try:
        manifest_raw = json.loads(manifest_file.read_text(encoding="utf-8"))
        manifest = CertificateManifest.model_validate(manifest_raw)

        # Check all file hashes
        for rel_file, expected_hash in manifest.files.items():
            f_path = path / rel_file
            if not f_path.exists():
                if verbose:
                    print(f"CHECK 1: File {rel_file} missing -> TAMPERED")
                    print("VERDICT: TAMPERED")
                return VerifyVerdict(verdict=VerifyVerdictKind.TAMPERED, reason=f"File {rel_file} missing")
            if compute_sha256(f_path) != expected_hash:
                if verbose:
                    print(f"CHECK 1: File {rel_file} SHA-256 mismatch -> TAMPERED")
                    print("VERDICT: TAMPERED")
                return VerifyVerdict(verdict=VerifyVerdictKind.TAMPERED, reason=f"File {rel_file} SHA-256 mismatch")

        # Check overall manifest hash
        hasher = hashlib.sha256()
        for rel_p in sorted(manifest.files.keys()):
            hasher.update(f"{rel_p}:{manifest.files[rel_p]}".encode())
        if hasher.hexdigest() != manifest.manifest_hash:
            if verbose:
                print("CHECK 1: Manifest hash mismatch -> TAMPERED")
                print("VERDICT: TAMPERED")
            return VerifyVerdict(verdict=VerifyVerdictKind.TAMPERED, reason="Manifest root hash mismatch")

        if verbose:
            print("CHECK 1: Cryptographic manifest integrity verified (all SHA-256 digests match).")
    except Exception as exc:
        if verbose:
            print(f"CHECK 1: Exception during manifest check: {exc} -> TAMPERED")
            print("VERDICT: TAMPERED")
        return VerifyVerdict(verdict=VerifyVerdictKind.TAMPERED, reason=str(exc))

    # --- Step 2: Load Contracts & Reproduction Trace ---
    try:
        world_raw = json.loads((path / "world.json").read_text(encoding="utf-8"))
        world_spec = WorldSpec.model_validate(world_raw)

        sig_raw = json.loads((path / "signature.json").read_text(encoding="utf-8"))
        target_sig = FailureSignature.model_validate(sig_raw)

        repro_raw = json.loads((path / "repro.json").read_text(encoding="utf-8"))
        repro_actions = [Action.model_validate(a) for a in repro_raw]
    except Exception as exc:
        if verbose:
            print(f"CHECK 2: Parsing contract JSON failed: {exc} -> TAMPERED")
            print("VERDICT: TAMPERED")
        return VerifyVerdict(verdict=VerifyVerdictKind.TAMPERED, reason=str(exc))

    # --- Step 3: Rebuild World Environment ---
    world = World(world_spec)
    try:
        world.start()
        if verbose:
            print(f"CHECK 2: World environment reconstructed from world.json at {world.url}.")
    except Exception as exc:
        if verbose:
            print(f"CHECK 2: World start failed: {exc} -> UNRESOLVED_ENV")
            print("VERDICT: UNRESOLVED_ENV")
        return VerifyVerdict(verdict=VerifyVerdictKind.UNRESOLVED_ENV, reason=str(exc))

    # --- Step 4: Independent Playwright Replay ---
    reproduced_count = 0
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)

            for run_idx in range(replay_count):
                context = await browser.new_context(viewport={"width": 1280, "height": 720})
                page = await context.new_page()

                observed_error: FailureSignature | None = None

                # Listeners for first-party 5xx, page errors, console errors
                async def handle_response(res: Any) -> None:
                    nonlocal observed_error
                    try:
                        if res.status >= 500 and world.url in res.url:
                            req_path = "/" + res.url.split(world.url.rstrip("/"))[-1].lstrip("/")
                            observed_error = FailureSignature(
                                kind="http_5xx",
                                first_party_endpoint=req_path,
                                status=res.status,
                                message_norm=normalize_message(f"HTTP {res.status} on {req_path}"),
                            )
                    except Exception:
                        pass

                def handle_page_error(exc: Any) -> None:
                    nonlocal observed_error
                    msg = str(exc)
                    observed_error = FailureSignature(
                        kind="page_error",
                        error_type=type(exc).__name__,
                        message_norm=normalize_message(msg),
                    )

                page.on("response", handle_response)
                page.on("pageerror", handle_page_error)

                # Execute minimal reproduction actions
                for action in repro_actions:
                    if action.kind == ActionKind.GOTO:
                        target = action.value or "/"
                        if not target.startswith("http"):
                            target = f"{world.url.rstrip('/')}{target}"
                        await page.goto(target, wait_until="domcontentloaded")
                        await asyncio.sleep(0.3)
                    elif action.kind == ActionKind.CLICK and action.locator:
                        loc = None
                        if action.locator.role and action.locator.name:
                            loc = page.get_by_role(action.locator.role, name=action.locator.name)
                        elif action.locator.label:
                            loc = page.get_by_label(action.locator.label)
                        elif action.locator.testid:
                            loc = page.get_by_test_id(action.locator.testid)
                        elif action.locator.css_fallback:
                            loc = page.locator(action.locator.css_fallback)

                        if loc and await loc.count() > 0:
                            await loc.first.click(timeout=5000)
                            await asyncio.sleep(0.3)
                    elif action.kind == ActionKind.FILL and action.locator:
                        loc = None
                        if action.locator.role and action.locator.name:
                            loc = page.get_by_role(action.locator.role, name=action.locator.name)
                        elif action.locator.label:
                            loc = page.get_by_label(action.locator.label)
                        elif action.locator.testid:
                            loc = page.get_by_test_id(action.locator.testid)
                        elif action.locator.css_fallback:
                            loc = page.locator(action.locator.css_fallback)

                        if loc and await loc.count() > 0:
                            await loc.first.fill(action.value or "", timeout=5000)
                            await asyncio.sleep(0.2)

                await asyncio.sleep(0.5)
                await context.close()

                if observed_error and signatures_match(target_sig, observed_error):
                    reproduced_count += 1

            await browser.close()

    except Exception as exc:
        world.stop()
        if verbose:
            print(f"CHECK 3: Execution error during replay: {exc} -> UNRESOLVED_ENV")
            print("VERDICT: UNRESOLVED_ENV")
        return VerifyVerdict(verdict=VerifyVerdictKind.UNRESOLVED_ENV, reason=str(exc))

    world.stop()

    if verbose:
        print(f"CHECK 3: Replayed {replay_count} times; target signature reproduced {reproduced_count}/{replay_count}.")

    if reproduced_count >= replay_count // 2 + 1:
        if verbose:
            print("VERDICT: VALID")
        return VerifyVerdict(verdict=VerifyVerdictKind.VALID, reason=f"Reproduced {reproduced_count}/{replay_count}")
    else:
        if verbose:
            print("VERDICT: INVALID")
        return VerifyVerdict(verdict=VerifyVerdictKind.INVALID, reason=f"Only reproduced {reproduced_count}/{replay_count}")
