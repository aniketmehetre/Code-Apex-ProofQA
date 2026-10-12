"""Rule-based frontier explorer with loop avoidance and clean-world backtracking."""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from proofqa.browser.executor import execute
from proofqa.browser.harness import BrowserHarness
from proofqa.browser.perception import extract_candidate_actions, get_page_fingerprint
from proofqa.contracts import (
    Action,
    ActionKind,
    StateFingerprint,
    TapeEvent,
)
from proofqa.explore.inputs import get_field_input
from proofqa.explore.state_graph import StateGraph
from proofqa.tape.recorder import TapeRecorder
from proofqa.world.manager import World


@dataclass
class CandidateFinding:
    """Anomalous candidate identified by an oracle hook during exploration."""

    state: StateFingerprint
    action: Action
    action_prefix: list[Action]
    evidence_events: list[TapeEvent]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExplorationResult:
    """Summary of an exploration session."""

    steps_executed: int
    duration_seconds: float
    coverage: dict[str, Any]
    candidates: list[CandidateFinding]
    distinct_urls: list[str]
    tape_path: Path


class RuleBasedExplorer:
    """Autonomous rule-based explorer navigating state frontiers without LLM dependencies."""

    def __init__(
        self,
        world: World,
        budget_steps: int = 25,
        budget_depth: int = 6,
        budget_time_seconds: float = 60.0,
        seed: int = 42,
        output_dir: Path | str | None = None,
        sqlite_path: Path | str | None = None,
        proposer: Any = None,
    ) -> None:
        self.world = world
        self.budget_steps = budget_steps
        self.budget_depth = budget_depth
        self.budget_time_seconds = budget_time_seconds
        self.seed = seed
        self.output_dir = Path(output_dir) if output_dir else Path("results/explore")
        self.sqlite_path = Path(sqlite_path) if sqlite_path else (self.output_dir / "graph.db")
        self.proposer = proposer

        self.graph = StateGraph(self.sqlite_path)
        self.hooks: list[Callable[[StateFingerprint, Action, list[TapeEvent], list[Action]], None]] = []
        self.candidates: list[CandidateFinding] = []
        self.action_history: list[Action] = []

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def add_oracle_hook(
        self,
        hook: Callable[[StateFingerprint, Action, list[TapeEvent], list[Action]], None],
    ) -> None:
        """Registers a hook invoked after every step to detect oracle violations."""
        self.hooks.append(hook)

    def _is_trap(self, url_path: str) -> bool:
        """Detects adversarial trap pages designed to trap web agents."""
        return "/trap/" in url_path

    async def explore(self) -> ExplorationResult:
        """Executes budget-bounded exploration, updating state graph and recording tape."""
        rng = random.Random(self.seed)
        recorder = TapeRecorder(self.output_dir, world_origin=self.world.url)

        start_time = time.time()
        steps = 0
        current_depth = 0

        harness = BrowserHarness()
        async with harness:
            context, page = await harness.new_context()
            recorder.attach(page)

            # 1. Initialize root state at "/"
            await page.goto(f"{self.world.url.rstrip('/')}/", wait_until="domcontentloaded", timeout=10000)
            await asyncio.sleep(0.3)
            fp = await get_page_fingerprint(page)
            recorder.record_state(fp)

            candidates = await extract_candidate_actions(page, origin=self.world.url)
            current_state_id = self.graph.add_state(fp, candidates, depth=0)

            while steps < self.budget_steps and (time.time() - start_time) < self.budget_time_seconds:
                # Check for loop / trap conditions
                is_trap = self._is_trap(fp.url_path)
                visit_count = self.graph.graph.nodes[current_state_id]["visit_count"]

                # If on trap page visited more than once, prune and force backtrack
                untried_actions = self.graph.get_untried_actions(current_state_id)
                if is_trap and visit_count >= 1:
                    untried_actions = []

                # If no untried actions in current state or depth exceeded, backtrack!
                if not untried_actions or current_depth >= self.budget_depth:
                    nearest = self.graph.find_nearest_state_with_untried(current_state_id)
                    if not nearest:
                        # Full graph exhausted within budgets
                        break

                    # Backtrack by resetting world and replaying path from root
                    self.world.reset()
                    await page.goto(f"{self.world.url.rstrip('/')}/", wait_until="domcontentloaded", timeout=10000)
                    await asyncio.sleep(0.3)

                    replay_path = self.graph.path_from_root(nearest)
                    for path_action in replay_path:
                        if path_action.kind == ActionKind.GOTO:
                            val = path_action.value or "/"
                            target_u = val if val.startswith("http") else f"{self.world.url.rstrip('/')}{val}"
                            await page.goto(target_u, wait_until="domcontentloaded", timeout=10000)
                        else:
                            await execute(page, path_action)
                        await asyncio.sleep(0.15)

                    fp = await get_page_fingerprint(page)
                    current_state_id = nearest
                    current_depth = len(replay_path)
                    untried_actions = self.graph.get_untried_actions(current_state_id)
                    if not untried_actions:
                        break

                # Choose next action from untried
                untried_actions.sort(key=lambda a: (a.kind.value, a.id))
                selected_action = None
                if self.proposer:
                    try:
                        raw_text = await page.inner_text("body")
                    except Exception:
                        raw_text = ""
                    suggested = self.proposer.propose(
                        candidates=untried_actions,
                        page_text=raw_text,
                        state_summary=f"Path: {fp.url_path}, controls: {fp.control_count}",
                    )
                    if suggested:
                        selected_action = suggested[0]

                if selected_action is None:
                    selected_action = rng.choice(untried_actions)

                # Form filling value assignment
                if selected_action.kind == ActionKind.FILL:
                    val = get_field_input(selected_action.locator, steps, seed=self.seed)
                    selected_action = Action(
                        id=selected_action.id,
                        kind=selected_action.kind,
                        locator=selected_action.locator,
                        value=val,
                        params=selected_action.params,
                    )

                # Execute action
                step_start = time.time()
                if selected_action.kind == ActionKind.GOTO:
                    dest = selected_action.value or "/"
                    dest_url = dest if dest.startswith("http") else f"{self.world.url.rstrip('/')}{dest}"
                    try:
                        await page.goto(dest_url, wait_until="domcontentloaded", timeout=10000)
                    except Exception:
                        pass
                else:
                    await execute(page, selected_action)

                await asyncio.sleep(0.3)
                recorder.record_action(selected_action, duration_ms=(time.time() - step_start) * 1000)
                self.action_history.append(selected_action)

                # Observe resulting state
                new_fp = await get_page_fingerprint(page)
                recorder.record_state(new_fp)
                new_candidates = await extract_candidate_actions(page, origin=self.world.url)

                new_state_id = self.graph.add_state(new_fp, new_candidates, depth=current_depth + 1)
                self.graph.record_transition(current_state_id, selected_action, new_state_id, step=steps)

                # Notify oracle hooks
                for hook in self.hooks:
                    hook(new_fp, selected_action, recorder.events[-4:], list(self.action_history))

                current_state_id = new_state_id
                fp = new_fp
                current_depth += 1
                steps += 1

            await recorder.flush()

        coverage = self.graph.coverage_summary()
        return ExplorationResult(
            steps_executed=steps,
            duration_seconds=time.time() - start_time,
            coverage=coverage,
            candidates=self.candidates,
            distinct_urls=coverage["distinct_urls"],
            tape_path=recorder.tape_path,
        )
