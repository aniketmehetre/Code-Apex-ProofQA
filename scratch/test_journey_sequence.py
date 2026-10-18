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
            
            await page.goto(world.url + "/")
            await asyncio.sleep(0.5)
            
            for j_name, actions in journeys:
                print(f"\n--- STARTING JOURNEY: {j_name} ---")
                for act in actions:
                    cands = await extract_candidate_actions(page, origin=world.url)
                    g = ground_action(act, cands)
                    if g is None:
                        # try retry
                        await asyncio.sleep(0.3)
                        cands = await extract_candidate_actions(page, origin=world.url)
                        g = ground_action(act, cands)
                    print(f"  Step {act.id} ({act.kind.value}): grounded={g is not None}")
                    if g is None:
                        print(f"  FAILED ON STEP: {act.id}, locator={act.locator}")
                        for c in cands:
                            print(f"    kind={c.kind} role={c.locator.role if c.locator else None} testid={c.locator.testid if c.locator else None} name={ascii(c.locator.name) if c.locator and c.locator.name else None}")
                        break
                    if g.kind == ActionKind.GOTO:
                        dest = g.value or "/"
                        dest_url = dest if dest.startswith("http") else f"{world.url.rstrip('/')}{dest}"
                        if page.url.rstrip("/") == dest_url.rstrip("/"):
                            await page.reload(wait_until="domcontentloaded")
                        else:
                            await page.goto(dest_url, wait_until="domcontentloaded")
                        try:
                            await page.wait_for_selector(".product-card, .btn-primary, button, input", timeout=1500)
                        except Exception:
                            pass
                    else:
                        ok, err = await execute(page, g)
                        print(f"  Executed ok={ok}, err={err}")
                    await asyncio.sleep(0.3)

asyncio.run(main())
