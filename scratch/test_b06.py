import asyncio
from proofqa.contracts import WorldSpec, ActionKind, Locator, Action
from proofqa.world.manager import World
from proofqa.browser.harness import BrowserHarness
from proofqa.browser.executor import execute
from proofqa.tape.recorder import TapeRecorder
from proofqa.oracles.relations.tape_oracle import MetamorphicOracle
from proofbench.runner import DEV_BUGS

async def test_b06():
    spec = WorldSpec(app_id="shop_twin", bugs=DEV_BUGS, seed=1)
    with World(spec) as world:
        harness = BrowserHarness(headless=True)
        await harness.start()
        _, page = await harness.new_context()
        recorder = TapeRecorder("results/test_b06", world.url)
        recorder.attach(page)
        oracle = MetamorphicOracle()
        try:
            await page.goto(f"{world.url.rstrip('/')}/")
            await asyncio.sleep(0.5)

            # 1. Select Electronics
            act_filter = Action(id="f1", kind=ActionKind.SELECT, locator=Locator(role="combobox", name="Filter by Category", label="Filter by Category"), value="Electronics")
            ok, err = await execute(page, act_filter)
            print("Execute filter:", ok, err)
            await asyncio.sleep(1.0)

            # Inspect buttons after filter
            buttons = await page.query_selector_all("button:visible")
            print("Buttons after filter:")
            for b in buttons:
                txt = (await b.text_content() or "").strip().encode("ascii", "replace").decode("ascii")
                lbl = (await b.get_attribute("aria-label") or "")
                print(f"  btn: '{txt}' aria-label='{lbl}'")

            # 2. Click Page 2
            act_p2 = Action(id="p2", kind=ActionKind.CLICK, locator=Locator(role="button", name="Page 2", label="Page 2"))
            from proofqa.browser.executor import resolve_element
            el = await resolve_element(page, act_p2.locator)
            print("Resolved p2 element:", el)
            if el:
                print("  el text:", await el.text_content(), "aria-label:", await el.get_attribute("aria-label"), "outerHTML:", await el.evaluate("e => e.outerHTML"))
            ok, err = await execute(page, act_p2)
            print("Execute page 2:", ok, err)
            await asyncio.sleep(1.0)

            # Check network events
            print(f"Recorded {len(recorder.events)} events:")
            for ev in recorder.events:
                if type(ev).__name__ == "NetworkEvent":
                    print(f"  {ev.method} {ev.url} -> status={ev.status} blob_ref={ev.response_blob_ref}")

            findings = oracle.evaluate_transition(act_p2, recorder.events[-6:], [act_filter])
            print("Oracle findings:", findings)
        finally:
            await harness.close()

if __name__ == "__main__":
    asyncio.run(test_b06())
