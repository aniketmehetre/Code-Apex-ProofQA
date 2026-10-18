import asyncio
from proofqa.contracts import WorldSpec, Tier
from proofqa.pipeline import Pipeline
from proofqa.proof.replay import replay
from proofbench.runner import DEV_BUGS

async def test():
    spec = WorldSpec(app_id="shop_twin", bugs=DEV_BUGS, seed=1)
    pipeline = Pipeline(
        world_spec=spec,
        output_dir="results/test_debug",
        level="rules_probes_goexplore",
    )
    # We want to see what candidates are found and test replay on them
    from proofqa.world.manager import World
    with World(spec) as world:
        from proofqa.explore.explorer import RuleBasedExplorer
        from proofqa.oracles.hard_signals import HardSignalsOracle
        from proofqa.oracles.spec_claims import SpecClaimsOracle
        from proofqa.oracles.cross_layer import CrossLayerOracle
        from proofqa.oracles.relations.tape_oracle import MetamorphicOracle

        explorer = RuleBasedExplorer(
            world=world,
            budget_steps=35,
            seed=1,
            output_dir="results/test_debug/explore",
            level="rules_probes_goexplore",
        )

        hard_signals = HardSignalsOracle()
        spec_claims = SpecClaimsOracle(offline=True, fact_store=explorer.spec_facts)
        metamorphic = MetamorphicOracle()
        cross_layer = CrossLayerOracle()

        explorer.add_oracle_hook(hard_signals.hook)
        explorer.add_oracle_hook(spec_claims.hook)
        explorer.add_oracle_hook(metamorphic.hook)
        async def cl_hook(page, fp, action, events, history, api_res):
            await cross_layer.verify_consistency(page, api_res, history)
        explorer.add_async_oracle_hook(cl_hook)

        res = await explorer.explore()
        print("Exploration finished. Steps:", res.steps_executed)

        all_cands = (
            list(hard_signals.candidates)
            + list(spec_claims.candidates)
            + list(cross_layer.candidates)
            + list(metamorphic.candidates)
        )
        print(f"Discovered {len(all_cands)} candidates:")
        for idx, c in enumerate(all_cands):
            s = f"[{idx+1}] ID: {c.id}, Oracle: {c.oracle_class}, Sig: {c.signature.kind}/{c.signature.error_type}, Claim: {c.claim}"
            print(s.encode("ascii", "replace").decode("ascii"))
            steps_str = f"    Steps ({len(c.steps)}): {[a.kind.value + ':' + str(getattr(a.locator, 'name', '') or a.value or '') for a in c.steps]}"
            print(steps_str.encode("ascii", "replace").decode("ascii"))

        for idx, c in enumerate(all_cands):
            print(f"Replaying [{idx+1}] {c.id}...")
            rep = await replay(
                trace=c.steps,
                world_spec=spec,
                n=1,
                target_signature=c.signature,
            )
            print(f"  Reproduced: {rep.reproduced}, Fail count: {rep.fail_count}")

if __name__ == "__main__":
    asyncio.run(test())
