import asyncio
from proofqa.contracts import WorldSpec, ActionKind
from proofqa.world.manager import World
from proofqa.browser.harness import BrowserHarness
from proofqa.browser.perception import extract_candidate_actions
from proofqa.explore.journeys import get_canonical_journeys
from proofqa.explore.grounding import ground_action
from proofbench.runner import DEV_BUGS

async def check():
    spec = WorldSpec(app_id="shop_twin", bugs=DEV_BUGS, seed=1)
    with World(spec) as world:
        harness = BrowserHarness(headless=True)
        await harness.start()
        context, page = await harness.new_context()
        try:
            await page.goto(f"{world.url.rstrip('/')}/", wait_until="networkidle")
            candidates = await extract_candidate_actions(page, origin=world.url)
            print(f"Extracted {len(candidates)} candidates on /:")
            for c in candidates:
                s = f"  {c.kind.value} id={c.id} role={getattr(c.locator, 'role', '')} name={getattr(c.locator, 'name', '')} label={getattr(c.locator, 'label', '')} testid={getattr(c.locator, 'testid', '')}"
                print(s.encode("ascii", "replace").decode("ascii"))

            journeys = get_canonical_journeys(seed=1)
            print("\nTesting journey grounding:")
            for jname, acts in journeys:
                print(f"\nJourney: {jname} ({len(acts)} acts)")
                for a in acts:
                    if a.kind == ActionKind.GOTO:
                        print(f"  {a.kind.value} {a.value} -> PASS (GOTO)")
                    else:
                        g = ground_action(a, candidates)
                        loc_str = f"role={getattr(a.locator, 'role', '')} name={getattr(a.locator, 'name', '')} testid={getattr(a.locator, 'testid', '')}"
                        if g:
                            print(f"  {a.kind.value} {loc_str} -> MATCHED: id={g.id}")
                        else:
                            print(f"  {a.kind.value} {loc_str} -> FAILED TO GROUND!")

        finally:
            await harness.close()

if __name__ == "__main__":
    asyncio.run(check())
