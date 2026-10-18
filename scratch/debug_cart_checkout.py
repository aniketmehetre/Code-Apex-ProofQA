import asyncio
from proofqa.contracts import WorldSpec, Action, ActionKind, Locator
from proofqa.world.manager import World
from proofqa.browser.harness import BrowserHarness
from proofqa.browser.executor import execute
from proofqa.browser.perception import extract_candidate_actions
from proofqa.explore.grounding import ground_action, TELEMETRY
from proofqa.explore.journeys import get_canonical_journeys

async def main():
    spec = WorldSpec(app_id="shop_twin", bugs=["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09", "B10"], seed=1)
    world = World(spec)
    with world:
        harness = BrowserHarness()
        async with harness:
            context, page = await harness.new_context()
            journeys = get_canonical_journeys(token="SAVE10", seed=1)
            # Find cart_checkout
            cart_journey = next(j for j in journeys if j[0] == "cart_checkout")[1]
            
            await page.goto(world.url + "/")
            await asyncio.sleep(0.5)
            
            page.on("response", lambda r: print(f"  [NET] {r.status} {r.url} -> {r.status}"))
            for i, act in enumerate(cart_journey):
                cands = await extract_candidate_actions(page, origin=world.url)
                grounded = ground_action(act, cands)
                print(f"Step {i} ({act.id}): grounded={grounded is not None}")
                if grounded is None:
                    print(f"FAILED TO GROUND: act={act}")
                    print("ALL CANDIDATES:")
                    for c in cands:
                        print("  ", c.kind, c.locator)
                    print(f"Telemetry reasons: {TELEMETRY.dropped_reasons[-3:]}")
                    break
                ok, err = await execute(page, grounded)
                print(f"Step {i} ({act.id}): executed ok={ok}, err={err}")
                await asyncio.sleep(0.5)

asyncio.run(main())
