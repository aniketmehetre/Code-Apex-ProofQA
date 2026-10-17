# ProofQA 2.0: Recall and Output Plan (Antigravity prompts)

Team VOID MAIN. Written 17 Oct 2026. Scope: raise recall and improve system output, nothing else.

## 1. Scope

**In scope:** (1) recall on the ten dev bugs B01-B10 and on bugs the system has never seen, (2) system output: findings, certificates, reports, benchmark and dashboard views.

**Deliberately out:** Class F geometry oracle, invariant mining, request-level fuzzing, per-bug worker swarm, access-control checks, tape hash chain, a second app, slide and pitch work. None of these raise recall on the planted bugs or improve what the system emits.

## 2. What I changed after re-reviewing my earlier plan

| # | Weakness in the earlier plan | Fix in this plan |
| --- | --- | --- |
| 1 | The stage funnel could not tell 'explorer never got there' from 'oracle never fired'. | Prompt 1 adds a server-side request log and a reach predicate per bug, so stage 1 (trigger reached) is measured independently of ProofQA. |
| 2 | Held-out bugs came after the probes, which is easy to call tuning. | Prompt 2 writes held-out bugs and new decoys first, seals them with a hash, and uses separate seeds (101-110). |
| 3 | A fixtures file for promo codes can look like hard-coding SAVE10. | Tokens are harvested from the page first. Fixtures are a documented operator input. No built-in coupon dictionary. The bench reports a no-fixtures row. |
| 4 | I proposed new tape fields and a new tier while contracts.py is frozen (Rule 8). | Prompt 8 has a decision gate: zero contract change if possible, otherwise additive optional fields only, plus a test that every old certificate still verifies. |
| 5 | More recall means duplicate findings, which hurts precision and clutters output. | Prompt 9 clusters findings by signature. |
| 6 | Nothing stopped the explorer from reading bug flags or ground truth. | Prompt 2 adds an AST guard and a stripped-WorldSpec test, so when a judge picks any bug, ProofQA is provably blind to it. |
| 7 | Tokens harvested from page text are an injection surface. | Strict charset regex; used only as fill values, never as locators or URLs, never sent to an LLM. |
| 8 | HTML minlength or required can swallow boundary probes before any request is sent (B08 risk). | Prompt 0 checks it. Prompt 4 logs client-blocked probes as UNRESOLVED, never PASS. |
| 9 | The ablation needs toggleable modules. | Prompt 3 builds the explorer levels before any module exists. |
| 10 | SpecFacts would be imported by both the explorer and the oracles. | It lives in its own module with no LLM imports and is never imported by verify.py. |
| 11 | The live demo lets a judge choose a bug, so discovery has to work inside a time limit. | Prompt 10 times it and adds a blind-discovery demo with a recorded fallback. |
| 12 | The old timeline started 16 Oct. | Section 5 is compressed to 17-23 Oct and orders prompts by expected recall gain per hour. |

## 3. Bug to capability map

This is a hypothesis. The Prompt 1 funnel confirms or kills each row.

| Bug | What reaching it needs | Capability | Prompt |
| --- | --- | --- | --- |
| B01 qty 0 | Boundary value in the quantity field | Boundary probe | 4 |
| B02 two items, promo, remove, checkout | Deep state plus a promo token | Semantic state, Go-Explore, token pool, journeys only if still stuck | 4, 6, 7 |
| B03 badge after remove | Add then remove, Class D at that step | Inverse-pair probe, Class D every transition | 5 |
| B04 total ignores discount | Promo token, Class D | Token pool, Class D every transition | 4, 5 |
| B05 sort not restored | Change sort then revert | Revert probe | 5 |
| B06 filter leak on page 2 | Page 2 plus filter | Pairwise probe, filter-subset check at any offset | 5 |
| B07 address lost on reload | Login, save, reload | Auth bootstrap, reload probe | 4, 5 |
| B08 4-char password | Policy copy plus an under-length value | SpecFacts, Class C | 4 |
| B09 intermittent lock | Rapid repeated adds | Burst action, INTERMITTENT tier | 8 |
| B10 quote in search | Quote tokens in text fields | Boundary probe | 4 |

## 4. Rules header (paste at the top of every Antigravity session)

```text
PROJECT: ProofQA 2.0 (Code-Apex-ProofQA repo). Windows + PowerShell: use .\make.bat and .\.venv\Scripts\...
READ FIRST: AGENTS.md, docs/claims.md, docs/limits.md, proofqa/contracts.py, and any notes in docs/recall/.
NON-NEGOTIABLE: the 8 rules in AGENTS.md. Plus these for this work:
A. proofqa/explore, proofqa/llm and proofqa/spec never import the bug catalogue, the held-out catalogue, bench code or ground truth, and never reference bug IDs.
B. Probes and LLM proposals reach the browser only through ground_action() (grounded locators only).
C. All randomness is seeded. Same seed + same level = same actions.
D. Never edit the adjudicator or loosen an oracle just to raise recall. Oracle changes are allowed only if evidence-bound, covered by a decoy test, and logged in docs/recall/oracle_changes.md.
E. No number appears in the UI or docs unless the bench produced it and docs/claims.md lists it.
F. contracts.py is frozen. If a task seems to need a change, STOP and write the question to docs/recall/blockers.md.
WORKFLOW: work on branch recall-v2 (tag pre-recall-v2 first). Small commits. Before finishing: make test and make lint pass, decoys show 0 false positives, hijack rate is 0. Write docs/recall/NN_<name>.md covering what changed, files touched, commands run, bench numbers before and after.
```

Run one Antigravity session per prompt. For prompts 0, 4, 6 and 8 (the risky ones) ask it to show its plan and wait for your approval before editing, if your build offers a planning mode. Review the diff before merging.

## 5. Timeline (17-23 Oct)

Dates are carried over from the earlier plan (freeze 23 Oct, finale 24-25 Oct). Adjust if they moved.

| Day | Prompts | Exit check |
| --- | --- | --- |
| Sat 17 Oct | 0, 1, 2 | Audit written, funnel prints, held-out set sealed |
| Sun 18 Oct | 3, 4 | Boundary, token and auth probes in; funnel delta recorded |
| Mon 19 Oct | 5, 6 | Metamorphic probes and Go-Explore in |
| Tue 20 Oct | 7 (gate), 8 | B02 and B09 resolved or honestly bounded |
| Wed 21 Oct | 9, 10 | Reports, bench v2, blind demo |
| Thu 22 Oct | 11 (stretch, stop at midday), 12 | One held-out run, claims synced |
| Fri 23 Oct | none | Freeze. Clean-checkout test and demo rehearsal only |

## 6. Prompts

### Prompt 0: Audit (read-only)

```text
GOAL: Find out exactly why recall is 10%. Do NOT change source code. Create only docs/recall/00_audit.md and results/recall/00_baseline.json.
TASKS:
1. Map the code: one line each for the explorer, proposer, oracles A-E, noise filter, replay engine, ddmin, certificate builder, verify.py, bench adjudicator, and validate-menu.
2. Define 'dev split' exactly as the bench computes it today: which bugs and seeds count, where recall 10% comes from, and which single bug is currently found.
3. Run .\make.bat validate-menu for ALL ten IDs B01..B10 (the cheat sheet lists only six). Record verdict and steps before/after shrink per bug. If an ID errors, say why.
4. Run .\make.bat bench with the current explorer. For each bug and seed record: pages visited, controls clicked, forms filled and with which values, whether register/login ever happened, max cart size reached, whether the promo field was ever filled.
5. For each of B01-B10, read the Shop Twin implementation and write: the exact trigger condition; whether any randomness is seeded by the world seed (B09 especially); whether client-side validation (min, minlength, required) would block the trigger through the UI (B01, B08); whether login is needed; where required inputs such as the coupon code appear, if anywhere (UI text, placeholder, API response, help copy).
6. Check whether the Action contract and harness can express everything needed: fill, select, click, goto/reload, rapid repeated clicks. List gaps, do not fix them.
7. Check duplicates: can one bug produce several findings today? Is there clustering?
8. Check the tape: are request bodies recorded? Which UiFact types exist? How do Class B persistence and Class C obtain the written payload?
9. Check whether anything under proofqa/explore can currently import or read bug flags, ground truth or bench code.
OUTPUT: docs/recall/00_audit.md with a table [bug | trigger | reach needs | blocker today | oracle exists? | proposed capability] and a section 'Contract changes needed? yes/no and why'. No code edits.
```

### Prompt 1: Reach instrumentation and stage funnel

```text
GOAL: Make the bench say WHY each bug is missed. Do not change the explorer.
BUILD:
1. Server-side request log. The World manager passes a file path through an env var; middleware appends one JSON line per request (timestamp, method, path, query, status, body keys and the values needed for predicates). It is never exposed over HTTP, never written to the tape, and never importable from explore, oracles, cert or llm (add import-guard tests).
2. proofqa/bench/reach.py: one ReachSpec per bug B01-B10, written as a pure predicate over the request log, using the trigger conditions in docs/recall/00_audit.md. UI-only bugs (B03, B04, B05) use the API calls that must have occurred. Unit tests with hand-written logs, positive and negative.
3. Stage funnel per (bug, seed), recording the LAST stage reached: S1 trigger reached; S2 candidate finding emitted whose signature matches the bug via the EXISTING adjudication matcher (do not change it); S3 confirmed k-of-k; S4 shrunk and certified; S5 external verify VALID; S6 adjudicated true positive. Write results/funnel.json and print a table at the end of make bench.
4. Recall-vs-budget: record the action count at first certified finding per bug and print cumulative recall at budgets 25, 50, 100, 200, 400 actions.
5. Add --seeds and --jobs N flags to the bench (parallel seeds, Windows-safe, each World on its own ephemeral port).
6. Run on at least 10 seeds and commit the output as results/recall/01_baseline_funnel.json.
DONE WHEN: make test passes and the funnel table prints for all 10 bugs.
```

### Prompt 2: Held-out bugs, new decoys, blindness guard

```text
GOAL: Create the held-out set and new decoys BEFORE any explorer improvement, so recall gains cannot be called tuning.
1. Add held-out bug flags H01-H05 to Shop Twin in a separate file (proofqa/world/heldout.py) with their own ground truth (proofqa/bench/ground_truth_heldout.json) and a ReachSpec plus unit tests each:
   H01 negative quantity add -> HTTP 500 (same class as B01, different value).
   H02 search containing a double quote, percent sign or backslash -> HTTP 500 (same class as B10, different token).
   H03 sort by name fails to restore the original order after reverting (same relation as B05, different control).
   H04 a different profile field (for example display name or phone) is not persisted after reload (same relation as B07, different field).
   H05 a shorter coupon-then-modify sequence crashes at checkout, on a path different from B02's.
   Held-out evaluation uses seeds 101-110. Dev uses 1-10.
2. Add decoys D06-D10, each documented as intended behaviour: D06 equal-price items may legitimately reorder; D07 a UI preference stored on this device only, with copy saying so; D08 an out-of-range quantity returns a friendly 400; D09 filter and page state reset on reload by design; D10 a rapidly-hit endpoint returns friendly 429 or 409, never 5xx.
3. Extend the ground truth so the bench reports D01-D05 and D06-D10 separately.
4. Blindness guard: an AST test that proofqa/explore, proofqa/llm and proofqa/spec cannot import the bug catalogue, held-out catalogue, bench or ground truth, and a runtime test that the explorer receives a WorldSpec with the bug list stripped.
5. Seal: tag heldout-v1, and write the commit hash plus the SHA-256 of ground_truth_heldout.json into docs/recall/heldout_seal.md.
6. Do not run the explorer on held-out bugs yet. Prove each is triggerable by a scripted request sequence only.
NOTE: if a teammate can plant these bugs instead, prefer that. Otherwise run this in a fresh session that has not seen any probe code.
```

### Prompt 3: Explorer levels, probe registry, grounding choke point

```text
GOAL: Create the extension points every later module plugs into, without changing behaviour.
1. Explorer levels: monkey, rules, rules_probes, rules_probes_goexplore, full. Expose as a --level flag on the bench and CLI. Default stays the current behaviour ('rules') until the final freeze. Save results per level under results/recall/<level>/.
2. Probe protocol in proofqa/explore/probes/base.py: a Probe has name, applies(ctx) and plan(ctx) -> list[Action]. ProbeContext carries grounded controls, semantic state key, SpecFacts handle, token pool, fixtures, budget left and a seeded rng. The registry runs probes in deterministic order, with a per-probe budget and a per-state 'already tried' memo.
3. Grounding choke point: one function ground_action(action, grounded_controls) used by BOTH LLM proposals and probes. Ungrounded locators are dropped and counted. Fill values pass a sanitizer (length cap, no control characters). Tests for both.
4. Extend tests/test_adversarial_lab.py so the /about injection runs at every level; hijack rate must be 0.
5. Determinism test: same seed and level produce an identical list of ActionEvents.
6. Budget controls in config: max actions per run, per-path state cap (default 8), per-page probe cap.
7. No oracle changes and no contract changes.
DONE WHEN: make test and make lint pass and the bench at level 'rules' reproduces the Prompt 1 baseline exactly.
```

### Prompt 4: SpecFacts, forms, boundary probes, tokens, fixtures, auth

```text
GOAL: Generic input discovery. Boundary values and tokens come from the page, not from bug knowledge.
1. proofqa/spec/facts.py (NO llm imports; verify.py must never import it; add guard tests). A SpecFactStore keyed by subject (field name, label or endpoint) holding kind (min_len, max_len, min, max, step, pattern, required, enum), value, source (html_attr or copy), evidence text and page. Extraction is deterministic regex only: input attributes plus copy such as 'at least N characters', 'minimum N', 'no more than N', 'between A and B', 'N-M characters'. Bind a sentence to a field by shared keyword (password, quantity, email...). The store is global across visited pages, help and policy pages included. Page text is untrusted data.
2. Form model: group inputs and their submit control into a FormPlan. Baseline valid values by input type (email, password, number, text, tel, select first real option), deterministic by seed and satisfying known facts (for example password length at least max(min_len, 12)).
3. BoundaryProbe: for each field, starting from a valid baseline, change ONE field at a time through min-1, min, min+1, max, max+1, 0, -1, empty, a 5000-character string, ', ", %, backslash and a unicode string. With no facts, use the generic subset. Submit and let oracles judge. If client-side validation blocks the submit, record the probe as UNRESOLVED in the funnel and count it.
4. TokenPool: harvest candidates from DOM text near words like code, promo, coupon or voucher, from placeholders and from first-party API response strings. Regex ^[A-Za-z0-9_-]{3,24}$. Tokens are used ONLY as fill values, never as locators or URLs, never sent to an LLM. Operator fixtures: an optional fixtures file in WorldSpec (test account, known promo codes), shipped for the shop as fixtures/shop.yaml. No built-in coupon dictionary anywhere.
5. AuthBootstrap: on an auth wall (401 on a first-party call, redirect to login, or a login/register form), register with baseline valid values or use the fixtures account, then log in if needed. Every step is an ordinary tape action so replays and certificates stay hermetic.
6. Class C: extend to use the SpecFactStore. FAIL only if (a) an explicit fact with source evidence exists, (b) the probe-filled value violates it, and (c) the first-party write in the same transition returned 2xx. Evidence includes the fact text and page. Add a decoy test so D08 stays clean.
7. Run level rules_probes on the dev seeds and record the funnel delta against results/recall/01_baseline_funnel.json. Decoys D01-D10 must show 0 false positives.
```

### Prompt 5: Metamorphic probes and Class D every transition

```text
GOAL: Reach-side support for metamorphic relations and cross-layer checks, generic across controls. Probes only act; oracles judge.
1. RevertProbe: for every select, radio or toggle with at least two options, record the observed list signature (item identifiers from the main list or the latest first-party GET array), move to each non-initial option, then restore the initial option. Class B sort invariance, generalized to 'restoring the initial value restores the observable list', judges from the tape pattern, so it also works on traces the probe did not produce.
2. ReloadProbe: after any acknowledged first-party mutation (POST, PUT, PATCH, DELETE with 2xx), reload the same URL and re-read. Class B persistence compares the written payload with the later GET payload (payload level, not pixel level).
3. InversePairProbe: add then remove, apply then clear, check then uncheck. Pairs are matched by a documented lexicon plus proximity (docs/recall/lexicon.md).
4. PairwiseProbe: independent controls are state-only controls on one page that do not change the URL path (pagination, filter, sort, search). Try A then B, B then A, and A, B, A-revert.
5. Class D after EVERY transition (post-settle), not opportunistically. Skip when either side is absent. Keep the D04 banner masked.
6. Oracle gap closure: for any bug the Prompt 1 funnel shows as 'reached but not flagged', fix the oracle only in an evidence-bound way (for example filter-subset must compare each item's field with the active filter value at any page offset). Write the decoy test first. Log each change in docs/recall/oracle_changes.md. Never change a threshold just to raise recall.
7. Run level rules_probes again and record the funnel delta against Prompt 4. Decoys D06, D07 and D09 must stay at 0 false positives.
```

### Prompt 6: Semantic state and Go-Explore

```text
GOAL: Reach deep stateful states (B02-shaped) without scripting them.
1. SemanticState: extend the state key (normalized URL path + ARIA hash) with coarse buckets derived generically: numeric badge or total text bucketed 0, 1, 2, 3+; array lengths in recent first-party GET JSON (bucketed); distinct line-item count; a boolean for any JSON key matching coupon|promo|discount|voucher being truthy; auth state (token in storage or cookie, or a session endpoint returning 200 vs 401); page, sort and filter query params. Keep D04 masked. Cap states per path (config, default 8) and add a global visit cap so D05 trap pages cannot explode the graph.
2. GoExploreArchive: map state key -> shortest tape prefix, visit count, untried-control count, novelty score. Selection is a seeded weighted choice that favours few visits and many untried controls; ties break by sorted key. Return-to-cell = fresh World + replay the prefix. If the replay diverges (state key mismatch or UNRESOLVED) mark the cell stale and skip it.
3. At each selected cell, try every grounded control once (each product's add button is a distinct control; form groups use FormPlan with TokenPool values) and run the applicable probes. Archive every new state.
4. Budget split is configurable, default 50% frontier and 50% archive.
5. Tests: synthetic-app tests for the archive logic. A deterministic reach test on Shop Twin with ALL bugs off: the explorer reaches the state {two distinct items + discount applied} within N actions (this measures reach, not bug finding). D05 traps must not exceed the state cap.
6. Run level rules_probes_goexplore on the dev seeds and record the funnel delta. Decoys must stay at 0 false positives.
```

### Prompt 7: Journey mutation (decision gate)

```text
GOAL: Only if B02 or H05 is still stuck at funnel stage 1 after Prompt 6.
GATE: read results/funnel.json. If B02 reaches stage 1 or later in at least 70% of seeds, SKIP the build: write docs/recall/07_skipped.md with the funnel evidence and stop. (Do not run H05 yet; use the scripted reach test for it.)
IF STUCK:
1. Intent vocabulary for generic commerce and CRUD flows: add_item, remove_item, apply_code, clear_code, checkout, register, login, update_profile, search, sort, filter, paginate. Map each intent to grounded controls through the role/label lexicon in docs/recall/lexicon.md (shared with Prompt 5). An intent with no matching control is skipped as a planning skip, not a bug.
2. Seed journeys over intents (for example add_item, add_item, apply_code, checkout), then mutate them: delete a step, swap two steps, repeat one, insert the inverse, and prefer a different item on each add. Execute only through ground_action().
3. Small deterministic journey budget; report the funnel per level.
Do NOT hard-code B02's exact sequence, any coupon code, or any shop-specific selector.
```

### Prompt 8: Burst action and INTERMITTENT tier (B09)

```text
GOAL: Make intermittent bugs certifiable honestly, with Rule 3 intact.
0. Read the B09 section of docs/recall/00_audit.md. Is the failure seeded by the world seed (deterministic by request order) or truly stochastic?
   CASE A (seeded): fix reach first (repeat the add action). ddmin changes the request count and so moves the failure; accept a reduction only if the exact signature still reproduces. No new tier needed. Stop after this.
   CASE B (stochastic, about 1 in 3 per request): continue.
1. Contract decision gate. Try a design with ZERO contract change first. If a new Action field is unavoidable, make it ADDITIVE and OPTIONAL: burst: int = 1 (N concurrent dispatches of the same grounded click, recorded as one tape event), omitted from serialization when default. Bump the minor contracts_version. Add a test proving every certificate already in results/ still verifies byte for byte. If anything beyond that is needed, STOP and write docs/recall/blockers.md.
2. BurstProbe: for add-to-cart-like and other mutating controls, dispatch N (default 5) concurrent repeats from a fresh state.
3. Tier INTERMITTENT. VERIFIED (k-of-k) stays untouched. INTERMITTENT = exact signature lock + m-of-n (default 2-of-5 bursts, each on a fresh world with a different seed). claim.json records the tier and the observed rate (for example 4/5).
4. verify.py: new verdict VALID_INTERMITTENT, distinct from VALID. Same Rule 3 isolation: no imports of explore, oracles, llm or uncertainty.
5. ddmin for INTERMITTENT: same m-of-n acceptance and the exact signature lock; keep the smallest burst size that still triggers.
6. Negative control: run the same burst trace at least 30 times on worlds with B09 disabled and require 0 signature hits. Save the result for a claim. D10 (friendly 429/409) must stay clean.
7. Never describe an INTERMITTENT certificate as 100% reproducible in UI or docs. Show the rate.
SANITY MATH (put in docs): at 1/3 per request a 5-burst triggers about 87% of the time. Strict 3-of-3 would pass only about 65% of runs; 2-of-5 passes about 99.9%.
```

### Prompt 9: Finding clustering and report output

```text
GOAL: Better system output without changing the certificate contract.
1. Finding clustering. Cluster key = oracle class + signature kind + normalized endpoint + status + error_type + message_norm. One finding per cluster, keeping the minimal trace and counting occurrences. The bench adjudicator stays unchanged; duplicates must not inflate precision or recall. Test with a synthetic double find.
2. proofqa report <cert> writes report.md OUTSIDE the sealed certificate directory, derived only from the certificate files: a title from oracle class + signature; numbered steps in plain English built from the Action locators (for example click button 'Add to Cart'); expected vs observed from per-class templates; evidence snippets from replay.json; the exact proofqa verify command; the tier and observed reproduction rate. Templates only, no LLM.
3. Run report (results/<run>/run_report.md and JSON): unique bugs found with actions and seconds to first find; coverage (pages, distinct semantic states, controls exercised, probes fired per family); suppressed noise counts (third-party errors, friendly 404s, masked banner changes); UNRESOLVED counts including client-blocked probes.
4. Expose both in the dashboard Inspector (download button) and the CLI. Everything is derived at render time: no schema change.
5. Tests: the report for demo_b01 matches repro.json step for step (golden file).
```

### Prompt 10: Bench v2, dashboard views, blind demo

```text
GOAL: Make the recall evidence visible and the live demo robust.
1. Bench v2 reports dev (B01-B10, seeds 1-10) and held-out (H01-H05, seeds 101-110) separately. Show trial-level recall (bug x seed) with Wilson 95% CI AND bug-level recall (found in at least 50% of seeds); precision with CI; decoy false positives for D01-D05 and D06-D10 separately; hijack rate; median actions and seconds to first certificate. Parallel seeds via --jobs.
2. Ablation ladder via --level: monkey with our oracles, rules, rules_probes, rules_probes_goexplore, full. Table plus chart. Include a no-fixtures row (fixtures disabled) so fixture dependence is visible.
3. New /bench panels, fed only from result JSON (no typed numbers): per-bug x seed heatmap (dev and held-out separately), stage funnel, recall-vs-budget curve.
4. Race Lane: live counters of certified unique bugs for ProofQA vs the monkey.
5. make demo-blind: ProofQA explores Shop Twin with all dev bugs enabled and NO hints for a fixed budget, streams certified findings, then runs the external verifier on each. Save the event stream to results/demo_blind_cache/. Add --replay-recorded to replay the saved stream, clearly labelled 'recorded run', as a fallback. Measure runtime on the presentation laptop; target under about 3 minutes.
6. make validate-menu <ID> for every ID. If it is currently scripted, add a blind-discovery mode (explorer with only that bug enabled, no hints) and keep the scripted mode as --scripted. Make blind the default only if its recall is at least 90% and its median time is under 60 seconds; otherwise keep scripted as the default.
```

### Prompt 11 (stretch): LLM journey proposer

```text
STRETCH. Hard stop at midday 22 Oct. Skip if behind; the plan stands without it.
GOAL: Show the LLM's measurable contribution without breaking determinism or the rules.
1. Extend proofqa/llm/proposer.py. Input: grounded controls and a sanitized SpecFacts summary (page text escaped and marked untrusted). Output: an ordered list of INTENTS from the Prompt 7 vocabulary. Not locators, not URLs. Validate against the vocabulary, map to grounded controls by the shared lexicon, and pass through ground_action().
2. Cache proposals keyed by hash(state key, control set, prompt version) in results/llm_cache/. With OFFLINE=1 use the cache or skip. The bench must run fully offline from the cache.
3. Level full = rules_probes_goexplore + journeys + LLM proposals. Compare with the previous level in the ablation and report the result honestly even if the gain is zero.
4. Rule 2 stays intact (proof, cert and oracles never import llm). The /about injection must change no action at level full (0 hijacks).
```

### Prompt 12: One held-out run and claims sync

```text
GOAL: One honest held-out evaluation and a consistent set of claims.
1. Freeze: tag recall-final-candidate. No explorer or oracle edits after this point.
2. Run the held-out set ONCE on seeds 101-110 for every level and save to results/heldout_final/. Record the commit hash and the heldout_seal.md hash in docs/claims.md. If any explorer or oracle code changes after seeing held-out results, mark held-out as 'used for tuning' in docs/limits.md and report it that way.
3. docs/claims.md: add one entry per claim, each with the number, its CI, the command that produced it and the result file: dev recall (trial and bug level), held-out recall, precision with the new counts, decoy false positives on both sets, intermittent tier (observed rate and the 0/N negative control), median time to first certificate, hijacks at every level, ablation contributions. Extend the claims audit in tests/test_redteam.py to read the result JSON and fail on any mismatch.
4. Sync docs: update the numbers in COMPLETE_PROJECT_GUIDE.md (Section 7 table, claims list), add the INTERMITTENT tier to Sections 5 and 6, add the judge question 'Why was your recall 10%?' with the honest funnel answer, and update docs/limits.md (unknown bug classes, e-commerce/CRUD lexicon scope, fixtures assumption, small held-out n).
5. On a clean checkout of the presentation machine (fresh clone, pip install, playwright install): make test, make lint, make bench, make demo and make demo-blind all pass.
```

## 7. What can still go wrong

| Risk | Fallback |
| --- | --- |
| B08 is blocked by client-side validation (the browser stops the submit) | Prompt 0 detects it. Do not bypass browser validation. Report B08 as bounded in docs/limits.md and show the UNRESOLVED count. |
| B02 and B04 need a promo code that appears nowhere on the page | Use the fixtures file and show the no-fixtures row in the ablation. |
| B09 turns out to be seeded (Case A) | Skip the tier. Fix reach and keep VERIFIED only. |
| New probes add false positives | Every prompt ends with the decoy gate. Stop and fix before moving on. |
| Time runs out | Cut in this order: 11, then 7 (if the gate skips it), then report polish in 9. Never cut 0-6, 8, 10 or 12. |
| Live demo misbehaves | Use demo-blind --replay-recorded, labelled as a recorded run. |

## 8. What each kind of judge will see

| Judge | Evidence |
| --- | --- |
| Engineering rigor | Import firewalls extended to new modules, deterministic seeded runs, additive-only contract rule with an old-certificate test |
| Research / ML | Ablation ladder, trial-level recall with Wilson CIs, sealed held-out set on separate seeds, fixtures-off row |
| Product / QA | report.md per certificate, clustered unique findings, run report with coverage and suppressed noise |
| Skeptic | Explorer provably blind to bug flags, 0% decoy false positives across 10 decoys, 0% hijacks at every level, honest INTERMITTENT rate with a negative control |
