import asyncio
from proofqa.contracts import WorldSpec, ActionKind, Locator, Action
from proofqa.world.manager import World
from proofqa.browser.harness import BrowserHarness
from proofqa.browser.executor import execute
from proofqa.browser.perception import extract_candidate_actions
from proofqa.explore.grounding import ground_action
from proofqa.tape.recorder import TapeRecorder
from proofqa.oracles.hard_signals import HardSignalsOracle
from proofbench.runner import DEV_BUGS

async def test_zero():
    spec = WorldSpec(app_id="shop_twin", bugs=DEV_BUGS, seed=1)
    with World(spec) as world:
        harness = BrowserHarness(headless=True)
        await harness.start()
        _, page = await harness.new_context()
        recorder = TapeRecorder("results/test_zero", world.url)
        recorder.attach(page)
        oracle = HardSignalsOracle()
        try:
            await page.goto(f"{world.url.rstrip('/')}/")
            cands = await extract_candidate_actions(page, origin=world.url)

            # Step 1: Click heading
            a1 = Action(id="j_click_prod", kind=ActionKind.CLICK, locator=Locator(role="heading", name="Noise-Canceling Wireless Headphones", label="Noise-Canceling Wireless Headphones", css_fallback=".product-title"))
            g1 = ground_action(a1, cands)
            print("Ground a1:", g1 is not None)
            ok1, err1 = await execute(page, g1)
            print("Exec a1:", ok1, err1)
            await asyncio.sleep(0.5)

            # Step 2: Fill 0
            cands2 = await extract_candidate_actions(page, origin=world.url)
            a2 = Action(id="j_zero_qty", kind=ActionKind.FILL, locator=Locator(role="spinbutton", name="Quantity", label="Quantity"), value="0")
            g2 = ground_action(a2, cands2)
            print("Ground a2:", g2 is not None)
            ok2, err2 = await execute(page, g2)
            print("Exec a2:", ok2, err2)
            await asyncio.sleep(0.5)

            # Step 3: Confirm modal add to cart
            cands3 = await extract_candidate_actions(page, origin=world.url)
            a3 = Action(id="j_confirm_zero_cart", kind=ActionKind.CLICK, locator=Locator(role="button", name="Add to Cart", testid="modal-add-to-cart", label="Confirm Add to Cart"))
            g3 = ground_action(a3, cands3)
            print("Ground a3:", g3 is not None)
            ok3, err3 = await execute(page, g3)
            print("Exec a3:", ok3, err3)
            await asyncio.sleep(0.5)

            fp = await recorder.flush()
            from proofqa.browser.perception import get_page_fingerprint
            fp_now = await get_page_fingerprint(page)
            oracle.hook(fp_now, g3, recorder.events[-6:], [g1, g2, g3])
            print("Oracle candidates:", oracle.candidates)
        finally:
            await harness.close()

if __name__ == "__main__":
    asyncio.run(test_zero())
