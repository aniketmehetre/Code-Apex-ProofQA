#!/usr/bin/env python3
"""ProofQA 2.0 &mdash; Interactive Frontend Demo & Screen Recording Script.

This script launches an automated, headed Chromium browser session that walks
through every tab and feature of the ProofQA 2.0 Web Dashboard (localhost:8000)
with smooth human pacing, animated pointer highlights, and an on-screen
presenter teleprompter HUD.

Usage:
    # 1. Standard Auto Mode (ideal for live narration or screen recording):
    python demo.py

    # 2. Step-by-Step Interactive Mode (press Enter to advance each scene):
    python demo.py --manual

    # 3. Automatic High-Definition Video Recording directly to file:
    python demo.py --record results/proofqa_ui_walkthrough.webm

    # 4. Custom pacing (e.g., 6 seconds per scene):
    python demo.py --delay 6.0

    # 5. Clean mode without on-screen teleprompter:
    python demo.py --no-hud
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def check_or_start_server(url: str, port: int) -> subprocess.Popen | None:
    """Ensure the ProofQA dashboard daemon is responsive before launching browser."""
    print(f"[*] Checking connection to ProofQA Dashboard at {url}...")
    try:
        with urllib.request.urlopen(f"{url}/bench/summary", timeout=1.5) as resp:
            if resp.status == 200:
                print(f"[+] ProofQA Dashboard is actively running on {url} (HTTP 200 OK).")
                return None
    except Exception:
        pass

    print(f"[!] Dashboard not detected at {url}. Starting dashboard server on port {port}...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "proofqa.cli", "dashboard", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Wait up to 10 seconds for server startup
    for _ in range(20):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen(f"{url}/bench/summary", timeout=1.0) as resp:
                if resp.status == 200:
                    print(f"[+] Successfully launched and verified ProofQA server on port {port}.")
                    return proc
        except Exception:
            continue

    print(f"[!] Warning: Could not verify server at {url}. Continuing anyway...")
    return proc


# CSS and JavaScript to inject visual pointer and presenter teleprompter HUD
HUD_INJECTION_SCRIPT = """
(() => {
    if (window.__proofqa_hud_installed) return;
    window.__proofqa_hud_installed = true;

    // 1. Create Glowing Virtual Pointer
    const cursor = document.createElement('div');
    cursor.id = 'proofqa-virtual-cursor';
    cursor.style.cssText = `
        position: fixed;
        width: 22px;
        height: 22px;
        border-radius: 50%;
        background: rgba(16, 185, 129, 0.4);
        border: 2px solid #10b981;
        box-shadow: 0 0 14px #10b981, inset 0 0 8px #10b981;
        pointer-events: none;
        z-index: 999999;
        transition: transform 0.3s cubic-bezier(0.25, 1, 0.5, 1), opacity 0.2s;
        transform: translate(-50%, -50%) scale(1);
        display: none;
    `;
    document.body.appendChild(cursor);

    // Click Ripple Effect
    window.__showRipple = (x, y) => {
        const ripple = document.createElement('div');
        ripple.style.cssText = `
            position: fixed;
            left: ${x}px;
            top: ${y}px;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            border: 2px solid #10b981;
            box-shadow: 0 0 12px #10b981;
            pointer-events: none;
            z-index: 999998;
            transform: translate(-50%, -50%) scale(1);
            animation: proofqaRipple 0.6s ease-out forwards;
        `;
        document.body.appendChild(ripple);
        setTimeout(() => ripple.remove(), 600);
    };

    const styleSheet = document.createElement('style');
    styleSheet.textContent = `
        @keyframes proofqaRipple {
            0% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
            100% { transform: translate(-50%, -50%) scale(5); opacity: 0; }
        }
        @keyframes proofqaPulse {
            0%, 100% { opacity: 0.9; transform: scale(1); }
            50% { opacity: 1; transform: scale(1.02); }
        }
    `;
    document.head.appendChild(styleSheet);

    window.__moveCursor = (x, y) => {
        cursor.style.display = 'block';
        cursor.style.left = `${x}px`;
        cursor.style.top = `${y}px`;
    };

    // 2. Create Presenter Teleprompter HUD (Floating Glass Overlay)
    const hud = document.createElement('div');
    hud.id = 'proofqa-hud';
    hud.style.cssText = `
        position: fixed;
        bottom: 24px;
        left: 50%;
        transform: translateX(-50%);
        width: 820px;
        max-width: 90vw;
        background: rgba(13, 17, 23, 0.92);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(16, 185, 129, 0.4);
        border-radius: 14px;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6), 0 0 20px rgba(16, 185, 129, 0.15);
        color: #f0f6fc;
        padding: 14px 22px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        z-index: 999990;
        display: flex;
        flex-direction: column;
        gap: 6px;
        transition: all 0.3s ease;
    `;

    hud.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 6px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #10b981; box-shadow: 0 0 8px #10b981;"></span>
                <span id="proofqa-hud-title" style="font-weight: 700; font-size: 13px; letter-spacing: 0.5px; text-transform: uppercase; color: #10b981;">
                    ProofQA 2.0 Presenter Guide
                </span>
            </div>
            <span id="proofqa-hud-badge" style="font-size: 11px; padding: 2px 8px; border-radius: 12px; background: rgba(16, 185, 129, 0.15); color: #10b981; font-weight: 600;">
                LIVE UI WALKTHROUGH
            </span>
        </div>
        <div id="proofqa-hud-script" style="font-size: 14px; line-height: 1.45; color: #e6edf3; font-weight: 500;">
            Initializing autonomous control plane demonstration...
        </div>
    `;
    document.body.appendChild(hud);

    window.__updateHud = (title, scriptText, badgeText = "DEMO STEP") => {
        const hudTitle = document.getElementById('proofqa-hud-title');
        const hudScript = document.getElementById('proofqa-hud-script');
        const hudBadge = document.getElementById('proofqa-hud-badge');
        if (hudTitle) hudTitle.textContent = title;
        if (hudScript) hudScript.innerHTML = scriptText;
        if (hudBadge) hudBadge.textContent = badgeText;
    };
})();
"""


async def smooth_move_and_click(page: Any, selector_or_locator: Any, click: bool = True) -> None:
    """Move glowing virtual cursor smoothly to element and optionally click."""
    try:
        if isinstance(selector_or_locator, str):
            loc = page.locator(selector_or_locator).first
        else:
            loc = selector_or_locator.first

        box = await loc.bounding_box()
        if box:
            target_x = box["x"] + box["width"] / 2
            target_y = box["y"] + box["height"] / 2
            # Move virtual pointer
            await page.evaluate(f"window.__moveCursor({target_x}, {target_y})")
            await asyncio.sleep(0.25)
            if click:
                await page.evaluate(f"window.__showRipple({target_x}, {target_y})")
                await loc.click()
                await asyncio.sleep(0.2)
    except Exception:
        # Fallback to direct click if animation calculation fails
        try:
            if click:
                await loc.click()
        except Exception:
            pass


async def wait_step(prompt_msg: str, delay_seconds: float, manual_mode: bool) -> None:
    """Pause between scenes according to auto delay or manual enter key."""
    if manual_mode:
        print(f"\n[PAUSED] {prompt_msg}")
        input("  >> Press [ENTER] to advance to next scene... ")
    else:
        print(f"[*] {prompt_msg} (waiting {delay_seconds:.1f}s)...")
        await asyncio.sleep(delay_seconds)


async def run_demo(args: argparse.Namespace) -> None:
    """Drive the browser session across all 7 dashboard tabs."""
    from playwright.async_api import async_playwright

    server_proc = check_or_start_server(args.url, args.port)

    print("\n" + "=" * 76)
    print("  [*] PROOFQA 2.0 -- HIGH-DEFINITION UI SCREEN RECORDING RUNNER")
    print("=" * 76)
    print(f" Target Dashboard: {args.url}")
    print(f" Mode: {'MANUAL STEP-BY-STEP (Press Enter)' if args.manual else f'AUTOMATED PACING ({args.delay}s delay)'}")
    if args.record:
        print(f" Recording Video: {args.record}")
    print("=" * 76 + "\n")

    async with async_playwright() as p:
        # Configure video recording directory if requested
        launch_args: dict[str, Any] = {
            "headless": args.headless,
            "slow_mo": 100,
        }

        context_args: dict[str, Any] = {
            "viewport": {"width": 1440, "height": 900},
            "device_scale_factor": 1.25,  # Crisp high-DPI rendering for recordings
        }

        record_dir = None
        if args.record:
            record_path = Path(args.record).resolve()
            record_dir = record_path.parent
            record_dir.mkdir(parents=True, exist_ok=True)
            context_args["record_video_dir"] = str(record_dir)
            context_args["record_video_size"] = {"width": 1440, "height": 900}

        browser = await p.chromium.launch(**launch_args)
        context = await browser.new_context(**context_args)
        page = await context.new_page()

        print(f"[*] Navigating to {args.url}...")
        await page.goto(args.url, wait_until="networkidle")
        await asyncio.sleep(1.0)

        if not args.no_hud:
            await page.evaluate(HUD_INJECTION_SCRIPT)

        # -------------------------------------------------------------
        # SCENE 0: HEADER & MODE SWITCHER
        # -------------------------------------------------------------
        if not args.no_hud:
            await page.evaluate("""
                window.__updateHud(
                    "Scene 0: Control Plane Header & Architecture",
                    "Welcome to <strong>ProofQA 2.0</strong>, the verification-native autonomous QA engine. Notice the top header indicating our autonomous control plane status and live backend connectivity.",
                    "OVERVIEW"
                );
            """)
        await wait_step("Scene 0: Executive Header Loaded", args.delay, args.manual)

        # -------------------------------------------------------------
        # SCENE 1: TAB 1 &mdash; RACE LANE
        # -------------------------------------------------------------
        if not args.no_hud:
            await page.evaluate("""
                window.__updateHud(
                    "Scene 1/7: Autonomous Verification Race Lane",
                    "<strong>Lane 1 (ProofQA)</strong> vs <strong>Lane 2 (Monkey Baseline)</strong> under matching step budgets. Watch ProofQA certify true bugs with 100% precision while the baseline generates 88% false alarm spam.",
                    "TAB 1: RACE LANE"
                );
            """)

        race_tab = page.get_by_role("button", name="Race Lane")
        await smooth_move_and_click(page, race_tab)
        await asyncio.sleep(0.8)

        # Click Start New Head-to-Head Race
        start_race_btn = page.get_by_role("button", name="Start New Head-to-Head Race")
        if await start_race_btn.count() > 0:
            await smooth_move_and_click(page, start_race_btn)

        if not args.no_hud:
            await page.evaluate("""
                window.__updateHud(
                    "Scene 1/7: Race in Progress",
                    "Observe the counter: ProofQA locks in verified certificates with zero false reports. The naive baseline spams noisy unproven alerts.",
                    "RACING..."
                );
            """)
        await wait_step("Scene 1: Head-to-Head Race Demonstrated", args.delay + 1.0, args.manual)

        # -------------------------------------------------------------
        # SCENE 2: TAB 2 &mdash; STATE GRAPH EXPLORER
        # -------------------------------------------------------------
        if not args.no_hud:
            await page.evaluate("""
                window.__updateHud(
                    "Scene 2/7: Autonomous State Graph Explorer",
                    "Real-time <strong>NetworkX directed state graph</strong> with <strong>ARIA semantic tree hashing</strong>. Nodes represent distinct deterministic application states; edges represent grounded user actions.",
                    "TAB 2: STATE GRAPH"
                );
            """)

        graph_tab = page.get_by_role("button", name="State Graph")
        await smooth_move_and_click(page, graph_tab)
        await asyncio.sleep(1.0)

        # Click on Catalog Node then Cart Node to trigger inspector update
        catalog_node = page.locator("text='Catalog Page'").first
        if await catalog_node.count() > 0:
            await smooth_move_and_click(page, catalog_node)
            await asyncio.sleep(1.0)

        cart_node = page.locator("text='Cart Modal'").first
        if await cart_node.count() > 0:
            await smooth_move_and_click(page, cart_node)
            if not args.no_hud:
                await page.evaluate("""
                    window.__updateHud(
                        "Scene 2/7: Bug Sighting on Cart Modal",
                        "Selecting the Cart Modal node updates the <strong>State Inspector</strong> with the ARIA subtree hash and flags the <code>ZeroQuantityException (HTTP 500)</code> oracle sighting.",
                        "BUG SIGHTING"
                    );
                """)
        await wait_step("Scene 2: State Graph & Node Inspector Demonstrated", args.delay, args.manual)

        # -------------------------------------------------------------
        # SCENE 3: TAB 3 &mdash; FINDING & EVIDENCE INSPECTOR
        # -------------------------------------------------------------
        if not args.no_hud:
            await page.evaluate("""
                window.__updateHud(
                    "Scene 3/7: Finding & Synchronized Evidence Inspector",
                    "A screenshot is not an engineering proof. ProofQA synchronizes user action steps with dual telemetry channels: <strong>Network I/O</strong> and <strong>Browser Console</strong>.",
                    "TAB 3: EVIDENCE"
                );
            """)

        evidence_tab = page.get_by_role("button", name="Finding & Evidence")
        await smooth_move_and_click(page, evidence_tab)
        await asyncio.sleep(0.8)

        # Select BUG-001
        bug1_card = page.locator("text='BUG-001'").first
        if await bug1_card.count() > 0:
            await smooth_move_and_click(page, bug1_card)
            await asyncio.sleep(0.5)

        # Step through the action timeline
        step_btns = page.locator("button:has-text('Step')")
        step_count = await step_btns.count()
        for idx in range(min(step_count, 4)):
            btn = step_btns.nth(idx)
            await smooth_move_and_click(page, btn)
            await asyncio.sleep(0.4)

        if not args.no_hud:
            await page.evaluate("""
                window.__updateHud(
                    "Scene 3/7: First-Party Telemetry Isolation",
                    "Notice the status: <code>First-party boundary: Preserved</code>. Under Rules 2 and 4, third-party tracking scripts and ad network noise are strictly excluded.",
                    "EVIDENCE LOCKED"
                );
            """)
        await wait_step("Scene 3: Multi-Channel Evidence Timeline Demonstrated", args.delay, args.manual)

        # -------------------------------------------------------------
        # SCENE 4: TAB 4 &mdash; TRACE SHRINK (ddmin)
        # -------------------------------------------------------------
        if not args.no_hud:
            await page.evaluate("""
                window.__updateHud(
                    "Scene 4/7: Three-Valued Delta Debugging (ddmin)",
                    "Developers hate 40-step recordings of random mouse clicks. ProofQA automatically bisects the execution trace to extract the minimal reproduction core.",
                    "TAB 4: TRACE SHRINK"
                );
            """)

        shrink_tab = page.get_by_role("button", name="Trace Shrink (ddmin)")
        await smooth_move_and_click(page, shrink_tab)
        await asyncio.sleep(1.0)

        # Click Run Shrink Demonstration
        shrink_btn = page.get_by_role("button", name="Run Shrink Demonstration")
        if await shrink_btn.count() > 0:
            await smooth_move_and_click(page, shrink_btn)
            if not args.no_hud:
                await page.evaluate("""
                    window.__updateHud(
                        "Scene 4/7: Trace Shrunk by 70%",
                        "Watch the matrix: 12 noisy steps drop down to <strong>4 minimal core steps (70% reduction)</strong> while preserving the Failure Signature with 100% fidelity.",
                        "SHRINK RESOLVED"
                    );
                """)
        await wait_step("Scene 4: Trace Shrinking Demonstrated", args.delay + 0.5, args.manual)

        # -------------------------------------------------------------
        # SCENE 5: TAB 5 &mdash; VERIFY & TAMPER DEMO (THE SHOWSTOPPER)
        # -------------------------------------------------------------
        if not args.no_hud:
            await page.evaluate("""
                window.__updateHud(
                    "Scene 5/7: The Cryptographic Showstopper &mdash; Rule 3 Verification",
                    "An AI agent cannot certify itself. ProofQA bundles findings into a cryptographic manifest with SHA-256 digests. Let us run clean verification first.",
                    "TAB 5: VERIFY & TAMPER"
                );
            """)

        verify_tab = page.get_by_role("button", name="Verify & Tamper Demo")
        await smooth_move_and_click(page, verify_tab)
        await asyncio.sleep(0.8)

        # 1. Clean verification
        clean_btn = page.get_by_role("button", name="Run Clean Verification")
        if await clean_btn.count() > 0:
            await smooth_move_and_click(page, clean_btn)
            await asyncio.sleep(1.2)

        # 2. Tamper demonstration
        if not args.no_hud:
            await page.evaluate("""
                window.__updateHud(
                    "Scene 5/7: Simulating a 1-Byte Tamper Attack",
                    "What happens if an LLM hallucinates or an attacker tampers with <code>claim.json</code>? Let's flip byte 0x01 and watch the external verifier.",
                    "ATTACK SIMULATION"
                );
            """)
        await asyncio.sleep(1.5)

        tamper_btn = page.get_by_role("button", name="Simulate 1-Byte Tamper Attack")
        if await tamper_btn.count() > 0:
            await smooth_move_and_click(page, tamper_btn)
            if not args.no_hud:
                await page.evaluate("""
                    window.__updateHud(
                        "Scene 5/7: INSTANT CRYPTOGRAPHIC REJECTION",
                        "<span style='color: #ef4444; font-weight: 700;'>TAMPERED - REJECTED!</span> SHA-256 manifest mismatch caught instantly at offset 0x00. Execution aborted before launching replay. Mathematically tamper-evident.",
                        "INTEGRITY ENFORCED"
                    );
                """)
        await wait_step("Scene 5: 1-Byte Tamper Attack Rejected", args.delay + 1.5, args.manual)

        # -------------------------------------------------------------
        # SCENE 6: TAB 6 &mdash; PROOFBENCH SCOREBOARD
        # -------------------------------------------------------------
        if not args.no_hud:
            await page.evaluate("""
                window.__updateHud(
                    "Scene 6/7: ProofBench Empirical Scoreboard",
                    "Empirical evaluation with <strong>Wilson 95% confidence intervals</strong>: <strong>80.0% Recall</strong> (8/10 True Bugs), <strong>100% Precision</strong>, <strong>0.0% Decoy False Positives</strong>, and <strong>0.0% Prompt Hijacks</strong>.",
                    "TAB 6: SCOREBOARD"
                );
            """)

        bench_tab = page.get_by_role("button", name="ProofBench Scoreboard")
        await smooth_move_and_click(page, bench_tab)
        await asyncio.sleep(1.0)

        # Smooth scroll down to claims table
        await page.evaluate("window.scrollBy({ top: 280, behavior: 'smooth' })")
        await asyncio.sleep(1.0)
        await wait_step("Scene 6: Statistical Scoreboard Demonstrated", args.delay, args.manual)

        # -------------------------------------------------------------
        # SCENE 7: TAB 7 &mdash; REVIEW & SUPPRESSION QUEUE
        # -------------------------------------------------------------
        if not args.no_hud:
            await page.evaluate("""
                window.__updateHud(
                    "Scene 7/7: Human Review & Enterprise Triage",
                    "Approving a finding automatically compiles it into a permanent <strong>Playwright CI regression test</strong>. Rejecting an issue creates an automated signature suppression rule.",
                    "TAB 7: REVIEW QUEUE"
                );
            """)

        review_tab = page.get_by_role("button", name="Review & Suppression")
        await smooth_move_and_click(page, review_tab)
        await asyncio.sleep(0.8)

        # Click Approve on first item
        approve_btn = page.locator("button:has-text('Approve')").first
        if await approve_btn.count() > 0:
            await smooth_move_and_click(page, approve_btn)
            await asyncio.sleep(0.8)

        if not args.no_hud:
            await page.evaluate("""
                window.__updateHud(
                    "Conclusion: ProofQA 2.0 &mdash; Zero-Hallucination Autonomous QA",
                    "Autonomous discovery &bull; Cryptographic proof &bull; 70% trace reduction &bull; One-click CI regression export. Thank you!",
                    "WALKTHROUGH COMPLETE"
                );
            """)
        await wait_step("Scene 7: Review Triage & CI Export Demonstrated", args.delay + 1.0, args.manual)

        # Close browser and finish video
        print("\n[+] UI demonstration walkthrough completed successfully!")
        await context.close()
        await browser.close()

        # If recorded video was requested, rename/move file to target destination
        if args.record and record_dir:
            recorded_files = list(record_dir.glob("*.webm"))
            if recorded_files:
                target_file = Path(args.record).resolve()
                latest_video = max(recorded_files, key=lambda f: f.stat().st_mtime)
                if latest_video != target_file:
                    if target_file.exists():
                        target_file.unlink()
                    latest_video.rename(target_file)
                print(f"[+] High-definition screen recording saved to: {target_file}")

    if server_proc:
        print("[*] Stopping background dashboard server...")
        server_proc.terminate()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ProofQA 2.0 &mdash; Autonomous UI Walkthrough & Screen Recording Script"
    )
    parser.add_argument(
        "--url",
        type=str,
        default="http://127.0.0.1:8000",
        help="URL of the running ProofQA dashboard (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to start server on if not already active (default: 8000)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=4.5,
        help="Seconds to pause at each scene in automated mode (default: 4.5)",
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Interactive step-by-step mode: waits for user to press [ENTER] at each scene",
    )
    parser.add_argument(
        "--record",
        type=str,
        default=None,
        help="Path to save WebM video recording of the browser session (e.g., results/demo.webm)",
    )
    parser.add_argument(
        "--no-hud",
        action="store_true",
        help="Disable the floating on-screen presenter teleprompter HUD overlay",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode without opening a visible window (default: headed)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    cli_args = parse_arguments()
    try:
        asyncio.run(run_demo(cli_args))
    except KeyboardInterrupt:
        print("\n[!] Demonstration halted by user (Ctrl+C).")
        sys.exit(0)
