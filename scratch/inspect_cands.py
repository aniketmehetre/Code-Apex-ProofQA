import asyncio
from proofqa.contracts import WorldSpec
from proofqa.proof.replay import replay
from proofbench.runner import BenchmarkRunner, DEV_BUGS

async def test():
    runner = BenchmarkRunner(seeds=[1], split="dev", level="rules_probes_goexplore", step_budget=35)
    # Get last candidates from explore
    from proofqa.pipeline import Pipeline
    spec = WorldSpec(app_id="shop_twin", bugs=DEV_BUGS, seed=1)
    pipeline = Pipeline(world_spec=spec, output_dir="results/recall/rules_probes_goexplore/certs_seed_1", level="rules_probes_goexplore")
    # Let's inspect pipeline.last_candidates or run explore quickly
    # Or load finding from results/recall/rules_probes_goexplore/certs_seed_1
    import glob
    print("Files in certs_seed_1:", glob.glob("results/recall/rules_probes_goexplore/certs_seed_1/**", recursive=True))

if __name__ == "__main__":
    asyncio.run(test())
