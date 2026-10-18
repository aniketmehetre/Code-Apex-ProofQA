import asyncio
from proofqa.contracts import WorldSpec, ActionKind, Locator, Action
from proofqa.world.manager import World
from proofqa.browser.harness import BrowserHarness
from proofqa.browser.executor import resolve_element, execute
from proofbench.runner import DEV_BUGS

async def test_resolve():
    spec = WorldSpec(app_id="shop_twin", bugs=DEV_BUGS, seed=1)
    with World(spec) as world:
        harness = BrowserHarness(headless=True)
        await harness.start()
        _, page = await harness.new_context()
        try:
            await page.goto(f"{world.url.rstrip('/')}/")
            
            # Test search quote
            act1 = Action(id="j_search_quote", kind=ActionKind.FILL, locator=Locator(role="searchbox", name="Search products", label="Search products"), value="'")
            ok1, err1 = await execute(page, act1)
            print("execute act1:", ok1, err1)

            from proofqa.browser.perception import extract_candidate_actions
            from proofqa.explore.grounding import ground_action
            cands_after_fill = await extract_candidate_actions(page, origin=world.url)
            print("cands_after_fill count:", len(cands_after_fill))

            # Test search submit
            act2 = Action(id="j_search_submit", kind=ActionKind.CLICK, locator=Locator(role="button", name="Search", label="Submit Search"))
            g2 = ground_action(act2, cands_after_fill)
            print("ground_action act2:", g2)
        finally:
            await harness.close()

if __name__ == "__main__":
    asyncio.run(test_resolve())
