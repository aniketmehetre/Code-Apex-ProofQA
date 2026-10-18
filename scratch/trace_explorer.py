import asyncio
from proofqa.contracts import WorldSpec
from proofqa.world.manager import World
from proofqa.explore.explorer import RuleBasedExplorer
from proofqa.explore.grounding import TELEMETRY
from proofbench.runner import DEV_BUGS

async def trace_explorer():
    spec = WorldSpec(app_id="shop_twin", bugs=DEV_BUGS, seed=1)
    with World(spec) as world:
        explorer = RuleBasedExplorer(
            world=world,
            budget_steps=35,
            seed=1,
            output_dir="results/test_trace",
            level="rules_probes_goexplore",
        )
        print("Starting trace exploration...")
        res = await explorer.explore()
        print("Exploration finished. Steps:", res.steps_executed)
        print("Action history:")
        for i, a in enumerate(explorer.action_history):
            print(f"  [{i}] {a.id} ({a.kind.value}) -> {getattr(a.locator, 'name', '') or getattr(a.locator, 'label', '') or a.value or ''}")
        print("Dropped reasons (first 10):", TELEMETRY.dropped_reasons[:10])

if __name__ == "__main__":
    asyncio.run(trace_explorer())
