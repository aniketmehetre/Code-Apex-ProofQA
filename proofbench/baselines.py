"""Competitive evaluation baselines running under identical budgets."""

from __future__ import annotations

import random
from typing import Any

from proofqa.contracts import (
    Action,
    ActionKind,
    FailureSignature,
    Finding,
    OracleClass,
    Tier,
    WorldSpec,
    normalize_message,
)
from proofqa.world.manager import World


class RandomMonkeyBaseline:
    """Baseline B1: Random monkey exploration with naive reporting.

    Reports ANY 4xx, 5xx, or console error naively without proof or shrinking.
    """

    def __init__(self, step_budget: int = 25, seed: int = 42) -> None:
        self.step_budget = step_budget
        self.seed = seed
        self.rng = random.Random(seed)

    async def run(self, world_spec: WorldSpec) -> list[Finding]:
        """Execute random actions and report every anomaly naively."""
        findings: list[Finding] = []
        world = World(world_spec)

        with world:
            from proofqa.browser.harness import BrowserHarness
            h = BrowserHarness()
            async with h:
                context, page = await h.new_context()

                observed_errors: list[dict[str, Any]] = []

                # Naive reporter listens to all responses (including 4xx and third-party)
                page.on(
                    "response",
                    lambda res: observed_errors.append({"status": res.status, "url": res.url})
                    if res.status >= 400
                    else None,
                )
                page.on(
                    "console",
                    lambda msg: observed_errors.append({"console": msg.text, "type": msg.type})
                    if msg.type == "error"
                    else None,
                )

                await page.goto(world.url)

                for step in range(self.step_budget):
                    # Randomly click buttons or links
                    buttons = await page.locator("button, a, input").all()
                    if buttons:
                        elem = self.rng.choice(buttons)
                        try:
                            tag = await elem.evaluate("el => el.tagName.toLowerCase()")
                            if tag == "input":
                                await elem.fill(f"monkey_{step}")
                            else:
                                await elem.click(timeout=1000)
                        except Exception:
                            pass

                # File finding for EVERY observed anomaly
                for idx, err in enumerate(observed_errors):
                    status = err.get("status")
                    url = err.get("url", "/unknown")
                    sig = FailureSignature(
                        kind="http_5xx" if status and status >= 500 else "http_4xx",
                        first_party_endpoint=url,
                        status=status,
                        message_norm=normalize_message(f"Naive anomaly: {err}"),
                    )
                    findings.append(
                        Finding(
                            id=f"monkey_finding_{idx}",
                            oracle_class=OracleClass.A,
                            tier=Tier.SUSPECTED,
                            signature=sig,
                            claim=f"Naive unproven anomaly: {err}",
                            steps=[Action(id="a0", kind=ActionKind.GOTO, value="/")],
                            confidence=0.5,
                        )
                    )

        return findings
