import asyncio
from proofbench.runner import BenchmarkRunner, DEV_BUGS

async def test():
    print("Starting BenchmarkRunner for seed 1...", flush=True)
    runner = BenchmarkRunner(
        seeds=[1],
        split="dev",
        level="rules_probes_goexplore",
        step_budget=35,
    )
    result = await runner._run_single_seed(seed=1, dev_bugs=DEV_BUGS)
    print("Seed 1 result:", flush=True)
    print("Certificates:", len(result.get("certificates", [])), flush=True)
    for c in result.get("certificates", []):
        print("  Cert:", c.get("path"), "verdict:", c.get("verdict"), flush=True)
    print("Decoy findings:", len(result.get("decoy_findings", [])), flush=True)
    print("Funnel:", flush=True)
    for bug, stages in result.get("funnel", {}).items():
        if stages.get("S6", 0) > 0 or stages.get("S1", 0) > 0 or stages.get("S2", 0) > 0:
            print(f"  {bug}: {stages}", flush=True)

if __name__ == "__main__":
    asyncio.run(test())
