import asyncio
from proofqa.contracts import WorldSpec, ActionKind, Locator, Action
from proofqa.world.manager import World
from proofqa.browser.harness import BrowserHarness
from proofqa.browser.executor import execute
from proofqa.browser.perception import extract_candidate_actions, get_page_fingerprint
from proofqa.explore.grounding import ground_action
from proofqa.tape.recorder import TapeRecorder
from proofqa.oracles.hard_signals import HardSignalsOracle
from proofqa.oracles.cross_layer import CrossLayerOracle
from proofqa.explore.journeys import get_canonical_journeys
from proofbench.runner import DEV_BUGS

async def test_checkout():
    spec = WorldSpec(app_id="shop_twin", bugs=DEV_BUGS, seed=1)
    with World(spec) as world:
        harness = BrowserHarness(headless=True)
        await harness.start()
        _, page = await harness.new_context()
        recorder = TapeRecorder("results/test_checkout", world.url)
        recorder.attach(page)
        hard_signals = HardSignalsOracle()
        cross_layer = CrossLayerOracle()

        try:
            await page.goto(f"{world.url.rstrip('/')}/")
            await asyncio.sleep(0.5)

            journeys = dict(get_canonical_journeys(token="SAVE10", seed=1))
            acts = journeys["cart_checkout"]
            executed = []

            for i, a in enumerate(acts):
                print(f"Step {i}: {a.id} ({a.kind.value})")
                if a.kind == ActionKind.GOTO:
                    await page.goto(f"{world.url.rstrip('/')}{a.value or '/'}")
                    g = a
                else:
                    cands = await extract_candidate_actions(page, origin=world.url)
                    g = ground_action(a, cands)
                    if not g:
                        print(f"  FAILED TO GROUND: {a.id} {a.locator}")
                        print(f"  Available candidates ({len(cands)}):")
                        for c in cands:
                            s = f"    {c.kind.value} id={c.id} role={getattr(c.locator, 'role', '')} name={getattr(c.locator, 'name', '')} label={getattr(c.locator, 'label', '')}"
                            print(s.encode("ascii", "replace").decode("ascii"))
                        break
                    from proofqa.browser.executor import resolve_element
                    el = await resolve_element(page, g.locator)
                    print(f"  Resolved {a.id}:", el)
                    if el:
                        print("    outerHTML:", await el.evaluate("e => e.outerHTML"))
                    ok, err = await execute(page, g)
                    print(f"  Exec: {ok} {err}")
                    if not ok:
                        break

                executed.append(g)
                if a.id in ("j_add_1", "j_add_2", "j_apply_coupon", "j_remove_item"):
                    await asyncio.sleep(0.8)
                else:
                    await asyncio.sleep(0.4)
                fp = await get_page_fingerprint(page)
                hard_signals.hook(fp, g, recorder.events[-6:], executed)
                await cross_layer.verify_consistency(page, recorder.last_api_responses, executed)

            print("\nHardSignals candidates:")
            for c in hard_signals.candidates:
                print(" ", c.id, c.signature.error_type, c.claim)

            print("\nCrossLayer candidates:")
            for c in cross_layer.candidates:
                print(" ", c.id, c.signature.error_type, c.claim)

        finally:
            await harness.close()

if __name__ == "__main__":
    asyncio.run(test_checkout())
