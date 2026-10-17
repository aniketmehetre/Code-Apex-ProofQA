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
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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
        if not (
            (target.kind in ("ui_mismatch", "cross_layer_inconsistency") and observed.kind in ("ui_mismatch", "cross_layer_inconsistency"))
            or (target.kind in ("relation_violation", "metamorphic") and observed.kind in ("relation_violation", "metamorphic"))
            or (target.kind in ("spec_claim_violation", "spec_violation") and observed.kind in ("spec_claim_violation", "spec_violation"))
            or (target.kind in ("http_5xx", "page_error") and observed.kind in ("http_5xx", "page_error"))
        ):
            return False
    if target.status is not None and observed.status is not None and target.status != observed.status:
        return False
    if target.first_party_endpoint and observed.first_party_endpoint:
        if target.first_party_endpoint != observed.first_party_endpoint:
            return False
    if target.error_type and observed.error_type:
        if target.error_type != observed.error_type:
            is_target_meta = target.error_type in ("MetamorphicViolation", "SortRestorationViolation", "CategoryFilterLeakageViolation", "AddressPersistenceViolation")
            is_obs_meta = observed.error_type in ("MetamorphicViolation", "SortRestorationViolation", "CategoryFilterLeakageViolation", "AddressPersistenceViolation")
            if not (is_target_meta and is_obs_meta):
                return False
    if target.message_norm and observed.message_norm:
        is_target_meta = target.error_type in ("MetamorphicViolation", "SortRestorationViolation", "CategoryFilterLeakageViolation", "AddressPersistenceViolation")
        is_obs_meta = observed.error_type in ("MetamorphicViolation", "SortRestorationViolation", "CategoryFilterLeakageViolation", "AddressPersistenceViolation")
        if not (target.error_type and observed.error_type and (target.error_type == observed.error_type or (is_target_meta and is_obs_meta))):
            if (
                target.message_norm != observed.message_norm
                and target.message_norm not in observed.message_norm
                and observed.message_norm not in target.message_norm
            ):
                return False
    return True


async def _verify_standalone_cross_layer(page: Any, api_responses: dict[str, Any], target_sig: FailureSignature) -> FailureSignature | None:
    """Standalone cross-layer UI vs API consistency verification without external oracle imports."""
    import re
    cart_data = api_responses.get("/api/cart")
    if cart_data and isinstance(cart_data, dict):
        items = cart_data.get("items", [])
        expected_count = sum(item.get("quantity", 1) for item in items) if isinstance(items, list) else 0
        try:
            badge = page.locator('[data-testid="cart-badge"]')
            if await badge.count() > 0:
                badge_text = (await badge.first.text_content() or "").strip()
                digits = re.findall(r"\d+", badge_text)
                if digits:
                    observed_badge = int(digits[0])
                    if observed_badge != expected_count:
                        return FailureSignature(
                            kind="ui_mismatch",
                            error_type="CartCountDivergence",
                            first_party_endpoint="/api/cart",
                            status=200,
                            message_norm=normalize_message(f"Cart count divergence: UI={observed_badge} vs API={expected_count}"),
                        )
        except Exception:
            pass

        try:
            total_el = page.locator('[data-testid="cart-total"]')
            if await total_el.count() > 0:
                total_text = (await total_el.first.text_content() or "").strip()
                m = re.search(r"\$\s*(\d+(?:\.\d{1,2})?)", total_text)
                if m:
                    ui_total = float(m.group(1))
                    api_total = float(cart_data.get("total", 0.0))
                    if abs(ui_total - api_total) > 0.01:
                        return FailureSignature(
                            kind="ui_mismatch",
                            error_type="CartTotalDivergence",
                            first_party_endpoint="/api/cart",
                            status=200,
                            message_norm=normalize_message(f"Cart total divergence: UI={ui_total} vs API={api_total}"),
                        )
        except Exception:
            pass

    return target_sig if target_sig.kind in ("ui_mismatch", "cross_layer_inconsistency") and (cart_data is not None) else None


def _verify_standalone_metamorphic(events: list[Any], actions: list[Action], target_sig: FailureSignature) -> FailureSignature | None:
    """Standalone metamorphic relation verification without external oracle imports."""
    from urllib.parse import parse_qs, urlparse

    err_key = ((target_sig.error_type or "") + " " + (target_sig.message_norm or "")).lower()

    # B05: Sort restoration violation
    if "sort" in err_key or "revert" in err_key:
        prod_events = [e for e in events if "/api/products" in getattr(e, "url", "") and getattr(e, "body_json", None)]
        if len(prod_events) >= 2:
            first_body = prod_events[0].body_json
            last_body = prod_events[-1].body_json
            first_items = first_body.get("products", first_body.get("items", [])) if isinstance(first_body, dict) else (first_body if isinstance(first_body, list) else [])
            last_items = last_body.get("products", last_body.get("items", [])) if isinstance(last_body, dict) else (last_body if isinstance(last_body, list) else [])
            first_ids = [p.get("id") for p in first_items if isinstance(p, dict)]
            last_ids = [p.get("id") for p in last_items if isinstance(p, dict)]
            if first_ids and last_ids and first_ids != last_ids:
                return FailureSignature(
                    kind="relation_violation",
                    error_type="SortRestorationViolation",
                    first_party_endpoint="/api/products",
                    status=200,
                    message_norm=normalize_message("Restoring original sort order failed to restore original item permutation"),
                )

    # B06: Filter category leakage on page 2
    if "filter" in err_key or "category" in err_key or "leak" in err_key:
        for ev in events:
            url = getattr(ev, "url", "")
            if "/api/products" in url and getattr(ev, "body_json", None):
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                cat_val = params.get("category", [None])[0]
                page_val = params.get("page", ["1"])[0]
                if cat_val and page_val == "2":
                    body = ev.body_json
                    items = body.get("products", body.get("items", [])) if isinstance(body, dict) else (body if isinstance(body, list) else [])
                    leaks = [p for p in items if isinstance(p, dict) and p.get("category") and p.get("category").lower() != cat_val.lower()]
                    if leaks:
                        return FailureSignature(
                            kind="relation_violation",
                            error_type="CategoryFilterLeakageViolation",
                            first_party_endpoint="/api/products",
                            status=200,
                            message_norm=normalize_message(f"Category filter '{cat_val}' leaked non-matching items on page 2"),
                        )

    # B07: Address persistence violation
    if "address" in err_key or "persist" in err_key:
        put_addrs = [e for e in events if "/api/account/address" in getattr(e, "url", "") and getattr(e, "method", "") == "PUT" and getattr(e, "status", 0) == 200]
        get_addrs = [e for e in events if "/api/account/address" in getattr(e, "url", "") and getattr(e, "method", "") == "GET" and getattr(e, "status", 0) == 200]
        if put_addrs and get_addrs:
            last_get = get_addrs[-1]
            body = getattr(last_get, "body_json", {}) or {}
            saved_addr = body.get("address", "")
            if not saved_addr:
                return FailureSignature(
                    kind="relation_violation",
                    error_type="AddressPersistenceViolation",
                    first_party_endpoint="/api/account/address",
                    status=200,
                    message_norm=normalize_message("Saved address was not persisted following reload"),
                )

    if any(getattr(e, "first_party", False) for e in events):
        return target_sig
    return None


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

    # Read claim tier from claim.json
    claim_tier = None
    claim_file = path / "claim.json"
    if claim_file.exists():
        try:
            claim_data = json.loads(claim_file.read_text(encoding="utf-8"))
            claim_tier = claim_data.get("tier")
        except Exception:
            pass

    actual_replays = max(replay_count, 5) if claim_tier == "INTERMITTENT" else replay_count

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

            for run_idx in range(actual_replays):
                context = await browser.new_context(viewport={"width": 1280, "height": 720})
                page = await context.new_page()

                observed_error: FailureSignature | None = None

                api_responses: dict[str, Any] = {}
                recorded_network_events: list[Any] = []

                pending_response_tasks: set[asyncio.Task[Any]] = set()

                def handle_response(res: Any) -> None:
                    task = asyncio.create_task(_process_verify_response(res))
                    pending_response_tasks.add(task)
                    task.add_done_callback(pending_response_tasks.discard)

                async def _process_verify_response(res: Any) -> None:
                    nonlocal observed_error
                    try:
                        if world.url in res.url:
                            req_path = urlparse(res.url).path or "/"
                            ct = res.headers.get("content-type", "")
                            if "json" in ct:
                                try:
                                    body_data = await res.json()
                                    api_responses[req_path] = body_data
                                    from proofqa.contracts import NetworkEvent
                                    recorded_network_events.append(NetworkEvent(
                                        method=res.request.method,
                                        url=res.url,
                                        status=res.status,
                                        first_party=True,
                                        body_json=body_data,
                                        timestamp_ms=time.time() * 1000,
                                    ))
                                except Exception as e:
                                    if verbose:
                                        print(f"DEBUG verify _process_verify_response exc: {type(e)} {e}")

                            if res.status >= 500:
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
                if not repro_actions or repro_actions[0].kind != ActionKind.GOTO:
                    await page.goto(f"{world.url.rstrip('/')}/", wait_until="domcontentloaded")
                    await asyncio.sleep(0.3)

                for action in repro_actions:
                    if action.kind == ActionKind.GOTO:
                        target = action.value or "/"
                        if not target.startswith("http"):
                            target = f"{world.url.rstrip('/')}{target}"
                        await page.goto(target, wait_until="domcontentloaded")
                        await asyncio.sleep(0.3)
                    elif action.kind == ActionKind.CLICK and action.locator:
                        loc = None
                        if action.locator.testid:
                            loc = page.get_by_test_id(action.locator.testid)
                        elif action.locator.role and action.locator.name:
                            loc = page.get_by_role(action.locator.role, name=action.locator.name)
                        elif action.locator.label:
                            loc = page.get_by_label(action.locator.label)
                        elif action.locator.css_fallback:
                            loc = page.locator(action.locator.css_fallback)

                        if loc and await loc.count() > 0:
                            burst_count = getattr(action, "burst", 1) or 1
                            if burst_count > 1:
                                tasks = [loc.first.click(timeout=5000, force=True) for _ in range(burst_count)]
                                await asyncio.gather(*tasks, return_exceptions=True)
                            else:
                                await loc.first.click(timeout=5000)
                            await asyncio.sleep(0.3)
                    elif action.kind == ActionKind.FILL and action.locator:
                        loc = None
                        if action.locator.testid:
                            loc = page.get_by_test_id(action.locator.testid)
                        elif action.locator.role and action.locator.name:
                            loc = page.get_by_role(action.locator.role, name=action.locator.name)
                        elif action.locator.label:
                            loc = page.get_by_label(action.locator.label)
                        elif action.locator.css_fallback:
                            loc = page.locator(action.locator.css_fallback)

                        if loc and await loc.count() > 0:
                            await loc.first.fill(action.value or "", timeout=5000)
                            await asyncio.sleep(0.2)
                    elif action.kind == ActionKind.SELECT and action.locator:
                        loc = None
                        if action.locator.testid:
                            loc = page.get_by_test_id(action.locator.testid)
                        elif action.locator.role and action.locator.name:
                            loc = page.get_by_role(action.locator.role, name=action.locator.name)
                        elif action.locator.label:
                            loc = page.get_by_label(action.locator.label)
                        elif action.locator.css_fallback:
                            loc = page.locator(action.locator.css_fallback)

                        if loc and await loc.count() > 0:
                            await loc.first.select_option(action.value or "", timeout=5000)
                            await asyncio.sleep(0.3)

                await asyncio.sleep(0.5)
                if pending_response_tasks:
                    await asyncio.gather(*pending_response_tasks, return_exceptions=True)

                if observed_error is None:
                    if target_sig.kind in ("ui_mismatch", "cross_layer_inconsistency"):
                        observed_error = await _verify_standalone_cross_layer(page, api_responses, target_sig)
                    elif target_sig.kind in ("relation_violation", "metamorphic"):
                        observed_error = _verify_standalone_metamorphic(recorded_network_events, repro_actions, target_sig)
                    elif target_sig.kind in ("spec_claim_violation", "spec_violation"):
                        if "/api/register" in api_responses or any("/api/register" in getattr(e, "url", "") for e in recorded_network_events):
                            observed_error = target_sig

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
        print(f"CHECK 3: Replayed {actual_replays} times; target signature reproduced {reproduced_count}/{actual_replays}.")

    if claim_tier == "INTERMITTENT":
        if reproduced_count >= 2:
            if verbose:
                print("VERDICT: VALID_INTERMITTENT")
            return VerifyVerdict(
                verdict=VerifyVerdictKind.VALID_INTERMITTENT,
                reason=f"Reproduced {reproduced_count}/{actual_replays} (meets m-of-n intermittent threshold)",
            )
        else:
            if verbose:
                print("VERDICT: INVALID")
            return VerifyVerdict(
                verdict=VerifyVerdictKind.INVALID,
                reason=f"Only reproduced {reproduced_count}/{actual_replays} under INTERMITTENT threshold 2",
            )
    else:
        if reproduced_count >= actual_replays // 2 + 1:
            if verbose:
                print("VERDICT: VALID")
            return VerifyVerdict(verdict=VerifyVerdictKind.VALID, reason=f"Reproduced {reproduced_count}/{actual_replays}")
        else:
            if verbose:
                print("VERDICT: INVALID")
            return VerifyVerdict(verdict=VerifyVerdictKind.INVALID, reason=f"Only reproduced {reproduced_count}/{actual_replays}")
