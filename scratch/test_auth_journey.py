import asyncio
from proofqa.contracts import WorldSpec, ActionKind, Locator, Action
from proofqa.world.manager import World
from proofqa.browser.harness import BrowserHarness
from proofqa.browser.executor import execute
from proofqa.browser.perception import extract_candidate_actions, get_page_fingerprint
from proofqa.explore.grounding import ground_action
from proofqa.tape.recorder import TapeRecorder
from proofqa.oracles.spec_claims import SpecClaimsOracle
from proofqa.explore.journeys import get_canonical_journeys
from proofbench.runner import DEV_BUGS

async def test_auth():
    spec = WorldSpec(app_id="shop_twin", bugs=DEV_BUGS, seed=1)
    with World(spec) as world:
        harness = BrowserHarness(headless=True)
        await harness.start()
        _, page = await harness.new_context()
        recorder = TapeRecorder("results/test_auth", world.url)
        recorder.attach(page)
        from proofqa.spec.facts import SpecFactStore
        fact_store = SpecFactStore()
        spec_claims = SpecClaimsOracle(offline=True, fact_store=fact_store)

        try:
            await page.goto(f"{world.url.rstrip('/')}/")
            await asyncio.sleep(0.5)

            acts = [
                Action(id="j_root_reg", kind=ActionKind.GOTO, value="/"),
                Action(id="j_nav_about", kind=ActionKind.CLICK, locator=Locator(role="button", name="About")),
                Action(id="j_auth_signin", kind=ActionKind.CLICK, locator=Locator(role="button", name="Sign In", label="Sign In")),
                Action(id="j_auth_signup", kind=ActionKind.CLICK, locator=Locator(role="button", name="Sign up here")),
                Action(id="j_fill_name", kind=ActionKind.FILL, locator=Locator(role="textbox", name="Full Name", label="Full Name"), value="Weak User"),
                Action(id="j_fill_email", kind=ActionKind.FILL, locator=Locator(role="textbox", name="Email Address", label="Email Address"), value="weak_user@example.com"),
                Action(id="j_fill_pw", kind=ActionKind.FILL, locator=Locator(role="textbox", name="Password", label="Password"), value="1234"),
                Action(id="j_click_reg", kind=ActionKind.CLICK, locator=Locator(role="button", name="Register", label="Register")),
            ]
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
                await asyncio.sleep(0.5)
                try:
                    ptext = await page.inner_text("body")
                    if ptext:
                        fact_store.extract_from_page_copy(ptext)
                except Exception:
                    pass
                fp = await get_page_fingerprint(page)
                spec_claims.hook(fp, g, recorder.events[-6:], executed)

            print("\nSpecClaims candidates:")
            for c in spec_claims.candidates:
                print(" ", c.id, c.signature.error_type, c.claim)
                from proofqa.proof.replay import replay
                rep = await replay(
                    trace=c.steps,
                    world_spec=spec,
                    n=1,
                    target_signature=c.signature,
                )
                print(f"  Reproduced: {rep.reproduced}, Fail count: {rep.fail_count}")

        finally:
            await harness.close()

if __name__ == "__main__":
    asyncio.run(test_auth())
