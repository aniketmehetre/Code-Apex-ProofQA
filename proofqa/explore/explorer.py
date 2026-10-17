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
from proofqa.explore.archive import GoExploreArchive
from proofqa.explore.auth import AuthBootstrap
from proofqa.explore.config import ExplorerConfig, ExplorerLevel
from proofqa.explore.forms import extract_form_plans
from proofqa.explore.grounding import ground_action, sanitize_input_value
from proofqa.explore.inputs import get_field_input
from proofqa.explore.probes.base import ProbeContext
from proofqa.explore.probes.boundary import BoundaryProbe
from proofqa.explore.probes.burst import BurstProbe
from proofqa.explore.probes.inverse import InversePairProbe
from proofqa.explore.probes.pairwise import PairwiseProbe
from proofqa.explore.probes.registry import ProbeRegistry
from proofqa.explore.probes.reload import ReloadProbe
from proofqa.explore.probes.revert import RevertProbe
from proofqa.explore.semantic_state import compute_semantic_state
from proofqa.explore.state_graph import StateGraph
from proofqa.explore.tokens import TokenPool
from proofqa.spec.facts import SpecFactStore
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
    """Autonomous explorer supporting configurable levels (monkey, rules, rules_probes, etc.)."""

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
        level: ExplorerLevel = "rules",
        probe_registry: ProbeRegistry | None = None,
        config: ExplorerConfig | None = None,
    ) -> None:
        self.world = world
        self.seed = seed
        self.output_dir = Path(output_dir) if output_dir else Path("results/explore")
        self.sqlite_path = Path(sqlite_path) if sqlite_path else (self.output_dir / "graph.db")
        self.proposer = proposer

        if config is not None:
            self.config = config
            if level != "rules":
                self.config.level = level
        else:
            self.config = ExplorerConfig(
                level=level,
                max_actions_per_run=budget_steps,
                budget_depth=budget_depth,
                budget_time_seconds=budget_time_seconds,
            )

        self.budget_steps = self.config.max_actions_per_run
        self.budget_depth = self.config.budget_depth
        self.budget_time_seconds = self.config.budget_time_seconds
        self.level = self.config.level
        self.spec_facts = SpecFactStore()
        fixtures_file = Path("fixtures/shop.yaml")
        self.token_pool = TokenPool(fixtures_path=fixtures_file if fixtures_file.exists() else None)

        self.probe_registry = probe_registry or ProbeRegistry(per_probe_budget=self.config.per_probe_budget)
        if self.level in ("rules_probes", "rules_probes_goexplore", "full"):
            self.probe_registry.register(BoundaryProbe())
            self.probe_registry.register(RevertProbe())
            self.probe_registry.register(ReloadProbe())
            self.probe_registry.register(InversePairProbe())
            self.probe_registry.register(PairwiseProbe())
            self.probe_registry.register(BurstProbe())

        self.graph = StateGraph(self.sqlite_path)
        self.hooks: list[Callable[[StateFingerprint, Action, list[TapeEvent], list[Action]], None]] = []
        self.async_hooks: list[Callable[[Any, StateFingerprint, Action, list[TapeEvent], list[Action], dict[str, Any]], Any]] = []
        self.candidates: list[CandidateFinding] = []
        self.action_history: list[Action] = []
        self.recorder: TapeRecorder | None = None
        self.archive = GoExploreArchive(max_cell_visits=self.config.global_visit_cap)

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def add_oracle_hook(
        self,
        hook: Callable[[StateFingerprint, Action, list[TapeEvent], list[Action]], None],
    ) -> None:
        """Registers a hook invoked after every step to detect oracle violations."""
        self.hooks.append(hook)

    def add_async_oracle_hook(
        self,
        hook: Callable[[Any, StateFingerprint, Action, list[TapeEvent], list[Action], dict[str, Any]], Any],
    ) -> None:
        """Registers an async hook invoked after every transition to detect cross-layer or DOM violations."""
        self.async_hooks.append(hook)

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
            self.recorder = recorder

            # 1. Initialize root state at "/"
            try:
                await page.goto(f"{self.world.url.rstrip('/')}/", wait_until="networkidle", timeout=10000)
            except Exception:
                await page.goto(f"{self.world.url.rstrip('/')}/", wait_until="domcontentloaded", timeout=10000)
                await asyncio.sleep(0.5)
            fp = await get_page_fingerprint(page)
            recorder.record_state(fp)

            try:
                page_text = await page.inner_text("body")
            except Exception:
                page_text = ""
            if page_text:
                self.spec_facts.extract_from_page_copy(page_text, page=fp.url_path)
                self.token_pool.harvest_from_text(page_text)

            candidates = await extract_candidate_actions(page, origin=self.world.url)
            self.token_pool.harvest_from_placeholders(candidates)
            current_state_id = self.graph.add_state(fp, candidates, depth=0)
            if self.level in ("rules_probes_goexplore", "full"):
                sem_state = await compute_semantic_state(page, fp, recorder.last_api_responses)
                self.archive.add_or_update(sem_state.key, [], candidates)

            probe_queue: list[Action] = []

            while steps < self.budget_steps and (time.time() - start_time) < self.budget_time_seconds:
                # ---------------- MONKEY LEVEL ----------------
                if self.level == "monkey":
                    if not candidates:
                        await page.goto(f"{self.world.url.rstrip('/')}/", wait_until="domcontentloaded", timeout=10000)
                        await asyncio.sleep(0.3)
                        fp = await get_page_fingerprint(page)
                        candidates = await extract_candidate_actions(page, origin=self.world.url)
                        if not candidates:
                            break

                    candidates.sort(key=lambda a: (a.kind.value, a.id))
                    selected_candidate = rng.choice(candidates)
                    if selected_candidate.kind == ActionKind.FILL:
                        val = get_field_input(selected_candidate.locator, steps, seed=self.seed)
                        selected_candidate = Action(
                            id=selected_candidate.id,
                            kind=selected_candidate.kind,
                            locator=selected_candidate.locator,
                            value=sanitize_input_value(val),
                            params=selected_candidate.params,
                        )
                    selected_action = ground_action(selected_candidate, candidates)
                    if selected_action is None:
                        selected_action = candidates[0]

                # ---------------- RULES & PROBES LEVELS ----------------
                else:
                    if probe_queue:
                        selected_action = probe_queue.pop(0)
                    else:
                        # Check for loop / trap conditions & per-path state cap
                        is_trap = self._is_trap(fp.url_path)
                        visit_count = self.graph.graph.nodes[current_state_id]["visit_count"]
                        path_state_count = self.graph.count_states_for_path(fp.url_path)

                        untried_actions = self.graph.get_untried_actions(current_state_id)
                        if (is_trap and visit_count >= 1) or path_state_count > self.config.per_path_state_cap:
                            untried_actions = []

                        # In Go-Explore levels, attempt return-to-cell if in archive phase or if state is exhausted
                        if self.level in ("rules_probes_goexplore", "full"):
                            archive_phase = steps >= int(self.budget_steps * (1.0 - self.config.archive_budget_fraction))
                            if archive_phase or not untried_actions or current_depth >= self.budget_depth:
                                cell = self.archive.select_cell(rng)
                                if cell and cell.prefix:
                                    self.world.reset()
                                    try:
                                        await page.goto(f"{self.world.url.rstrip('/')}/", wait_until="networkidle", timeout=10000)
                                    except Exception:
                                        await page.goto(f"{self.world.url.rstrip('/')}/", wait_until="domcontentloaded", timeout=10000)
                                        await asyncio.sleep(0.5)
                                    diverged = False
                                    for p_act in cell.prefix:
                                        if p_act.kind == ActionKind.GOTO:
                                            val = p_act.value or "/"
                                            target_u = val if val.startswith("http") else f"{self.world.url.rstrip('/')}{val}"
                                            await page.goto(target_u, wait_until="domcontentloaded", timeout=10000)
                                        else:
                                            ok, _ = await execute(page, p_act)
                                            if not ok:
                                                diverged = True
                                                break
                                        await asyncio.sleep(0.15)

                                    ret_fp = await get_page_fingerprint(page)
                                    ret_sem = await compute_semantic_state(page, ret_fp, recorder.last_api_responses)
                                    if diverged or ret_sem.key != cell.state_key:
                                        self.archive.mark_stale(cell.state_key)
                                    else:
                                        fp = ret_fp
                                        current_depth = len(cell.prefix)
                                        self.action_history = list(cell.prefix)
                                        candidates = await extract_candidate_actions(page, origin=self.world.url)
                                        current_state_id = self.graph.add_state(fp, candidates, depth=current_depth)
                                        untried_actions = self.graph.get_untried_actions(current_state_id)

                        # If no untried actions in current state or depth exceeded, backtrack via graph!
                        if not untried_actions or current_depth >= self.budget_depth:
                            nearest = self.graph.find_nearest_state_with_untried(current_state_id)
                            if not nearest:
                                # Full graph exhausted within budgets
                                break

                            # Backtrack by resetting world and replaying path from root
                            self.world.reset()
                            try:
                                await page.goto(f"{self.world.url.rstrip('/')}/", wait_until="networkidle", timeout=10000)
                            except Exception:
                                await page.goto(f"{self.world.url.rstrip('/')}/", wait_until="domcontentloaded", timeout=10000)
                                await asyncio.sleep(0.5)

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
                            candidates = await extract_candidate_actions(page, origin=self.world.url)
                            if not untried_actions:
                                break

                        selected_action = None

                        # Check if active probes apply at this state (rules_probes, rules_probes_goexplore, full)
                        if self.level in ("rules_probes", "rules_probes_goexplore", "full"):
                            # Check AuthBootstrap
                            if AuthBootstrap.is_auth_wall(fp.url_path, recorder.events[-5:], candidates):
                                auth_acts = AuthBootstrap.plan_login_or_register(
                                    candidates,
                                    fixtures=self.token_pool.fixtures,
                                    seed=self.seed,
                                )
                                if auth_acts:
                                    selected_action = auth_acts[0]
                                    probe_queue.extend(auth_acts[1:])

                            if selected_action is None and self.probe_registry.probes:
                                ctx = ProbeContext(
                                    grounded_controls=candidates,
                                    semantic_state_key=f"{fp.url_path}:{fp.aria_hash or fp.simhash}",
                                    spec_facts=self.spec_facts,
                                    token_pool=self.token_pool.get_tokens(),
                                    fixtures=self.token_pool.fixtures,
                                    budget_left=self.budget_steps - steps,
                                    rng=rng,
                                )
                                probe_acts = self.probe_registry.run_applicable_probes(
                                    ctx,
                                    max_probes_per_page=self.config.per_page_probe_cap,
                                )
                                if probe_acts:
                                    selected_action = probe_acts[0]
                                    probe_queue.extend(probe_acts[1:])
                                else:
                                    selected_action = None
                        else:
                            selected_action = None

                        if selected_action is None and self.level in ("rules_probes_goexplore", "full"):
                            form_plans = extract_form_plans(candidates)
                            for fplan in form_plans:
                                if any(a.id in {u.id for u in untried_actions} for a in fplan.fields):
                                    f_acts = fplan.generate_baseline_actions(
                                        fact_store=self.spec_facts,
                                        tokens=self.token_pool.get_tokens(),
                                        seed=self.seed,
                                    )
                                    if f_acts:
                                        selected_action = f_acts[0]
                                        probe_queue.extend(f_acts[1:])
                                        break

                        if selected_action is None:
                            # Choose next action from untried
                            untried_actions.sort(key=lambda a: (a.kind.value, a.id))
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
                                    g = ground_action(suggested[0], candidates)
                                    if g is not None:
                                        selected_action = g

                            if selected_action is None:
                                selected_action = rng.choice(untried_actions)

                            # Form filling value assignment
                            if selected_action.kind == ActionKind.FILL:
                                val = get_field_input(selected_action.locator, steps, seed=self.seed)
                                selected_action = Action(
                                    id=selected_action.id,
                                    kind=selected_action.kind,
                                    locator=selected_action.locator,
                                    value=sanitize_input_value(val),
                                    params=selected_action.params,
                                )

                # Choke point validation against current page candidates
                grounded = ground_action(selected_action, candidates)
                if grounded is not None:
                    selected_action = grounded

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

                try:
                    new_text = await page.inner_text("body")
                except Exception:
                    new_text = ""
                if new_text:
                    self.spec_facts.extract_from_page_copy(new_text, page=new_fp.url_path)
                    self.token_pool.harvest_from_text(new_text)
                self.token_pool.harvest_from_placeholders(new_candidates)

                new_state_id = self.graph.add_state(new_fp, new_candidates, depth=current_depth + 1)
                self.graph.record_transition(current_state_id, selected_action, new_state_id, step=steps)

                # Record in Go-Explore archive
                if self.level in ("rules_probes_goexplore", "full"):
                    new_sem_state = await compute_semantic_state(page, new_fp, recorder.last_api_responses)
                    self.archive.add_or_update(new_sem_state.key, list(self.action_history), new_candidates)
                    if hasattr(selected_action, "id"):
                        self.archive.record_action_tried(new_sem_state.key, selected_action.id)

                # Notify oracle hooks
                for hook in self.hooks:
                    hook(new_fp, selected_action, recorder.events[-6:], list(self.action_history))

                for ahook in self.async_hooks:
                    try:
                        await ahook(page, new_fp, selected_action, recorder.events[-6:], list(self.action_history), recorder.last_api_responses)
                    except Exception:
                        pass

                current_state_id = new_state_id
                fp = new_fp
                candidates = new_candidates
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
