# ProofQA 2.0: The Verification-Native Autonomous QA Engineer

*Team VOID MAIN. Code Apex, Track 2: Autonomous AI QA Engineer. Final project context, merging the PPT (ProofQA), both research reports, the TRACEFORGE dossier and the 12-upgrade list.*

## 1. The thesis

Every AI tester today produces an **opinion**: 'I think this is a bug.' Opinions need trust, and trust is exactly what developers have stopped giving to AI testers (false positives, un-reproducible reports, flaky output).

ProofQA 2.0 changes the unit of output. It does not file bug reports. It issues **Bug Certificates**: self-contained, machine-checkable proof objects that anyone can re-verify in a clean container with one command, without trusting the agent that produced them.

> **Do not trust the agent. Verify the certificate.**

Three principles hold the whole system together:

1. **The agent proposes, the world disposes.** The LLM may suggest actions and draft prose. It never decides whether something is a bug. Browser execution, deterministic oracles and independent re-verification decide.
2. **Every claim is a falsifiable experiment.** Each finding records the hypothesis, the experiment run, and the observed outcome. Nothing is asserted that the recorded tape cannot show.
3. **Know what you do not know.** The system calibrates its confidence, abstains when evidence is insufficient, and says which experiment would resolve the doubt.

**What this adds over the PPT's ProofQA:** a portable certificate format, a hermetic replay substrate, a cross-layer oracle (UI versus network truth), two-level shrinking (steps and input values), an uncertainty and abstention engine, an adversarial lab with a generated benchmark (ProofBench), calibrated confidence as a measured result, and a counterfactual comparison against baselines.

## 2. What we keep, merge and drop

| Source | Keep | Drop or fix |
| --- | --- | --- |
| PPT (ProofQA) | Detect, Prove, Shrink, Test; three oracles; trust tiers; four agents; benchmark with held-out bugs; Bug Lab | 'Proof' was never defined precisely; no statefulness handling in ddmin; no uncertainty or security story; leftover drafting notes on slides |
| Landscape report | State-graph coverage, confidence-verified reporting, flakiness and noise concerns | Cross-browser diffing as a core feature |
| Strategy report | Trace minimisation, metamorphic invariants, XPIA security, economics argument, red-team honesty | Falling back to LLM-guessed minimisation |
| TRACEFORGE dossier | Failure signatures, UNRESOLVED and inconclusive handling, claims discipline, three-level demo fallback, harness mindset | Crash-only oracle, optional LLM, no naive-LLM baseline, no calibration |
| 12-upgrade list | All twelve, each given a concrete role (section 15) | None |

## 3. The Bug Certificate (the central artifact)

A certificate is a directory or archive containing:

- **Claim:** one sentence plus the oracle class that supports it (section 5), with provenance (the spec sentence, or the relation name and its validation record).
- **Minimal reproduction:** the shrunk step list and the shrunk input values.
- **Failure signature:** normalised status, endpoint, error type and message, first-party frames. Replays must match this signature, not merely 'any failure'.
- **Replay record:** k of n fresh-world replays reproduced it, with an interval estimate, plus any intermittency measure.
- **World descriptor:** pinned container image digests, browser version, seed, frozen clock, recorded network, DB snapshot id. This is what makes replay portable.
- **Evidence bundle:** Playwright trace, video, HAR, console log, screenshots, DOM snapshots at each step.
- **Exported test:** a Playwright test that fails on the buggy build and passes on the fixed build where one exists.
- **Honest-limits block:** what the certificate does and does not establish.

Command: `proofqa verify <certificate>` rebuilds the world from the descriptor, replays the minimal reproduction in a clean container, and prints VALID or INVALID with reasons. The checker shares no code path with the agent. This is the independent verification engine, and it is also the scenario-replay feature.

**What a certificate proves:** a reproducible, minimal, signature-stable behaviour that violates a stated oracle. **What it does not prove:** product intent. Classes B to E in section 5 therefore carry an explicit 'needs intent confirmation' flag.

## 4. Architecture: ten layers

**L0. Hermetic runtime (digital twin and replay substrate).** Target app and dependencies in containers. Controlled time, seeded randomness, recorded and replayable network, copy-on-write database snapshots so every replay starts from the exact same world. Pinned image digests for portability.

**L1. Perception and state.** ARIA-snapshot perception. Normalised state fingerprint (volatile text removed, similarity hashing). Noise-floor calibrator: an idle visit first records pre-existing console and network noise, which is subtracted later. Widget classifier labels lists, search boxes, sort controls, carts, paginators and forms so the right relations can be bound.

**L2. Exploration brain.** The state graph (networkx, persisted) lives outside the LLM. The frontier policy scores candidate actions by novelty, uncertainty and risk. The LLM only proposes semantic actions and form values, and it picks from a numbered list the deterministic layer supplies. It cannot invent URLs or code.

**L3. Oracle stack.** Five oracle families (section 5), each a plug-in, each with a declared proof strength.

**L4. Proof engine.** Fresh-world replay k of n, signature matching, flake estimation, hierarchical shrinking, memoised and parallel replays (section 6).

**L5. Evidence and certificate.** Tape recorder, certificate builder, evidence explorer, and a grounded reporter whose every sentence is checked against the tape.

**L6. Uncertainty and decision.** Confidence composition, abstention, next-best-experiment selection, calibration tracking (section 7).

**L7. Human review and learning.** Review queue ordered by value of information. Reviewer decisions become suppression rules and relation priors (section 11).

**L8. Delivery.** Playwright suite with a mutation-scored strength metric, GitHub Action, PR comment bot, issue export, nightly drift reports.

**L9. Assurance lab (ProofBench).** Bug mutator, generated app twins, adversarial pages, baselines, scoreboard. This is how we prove every claim above (sections 9 and 13).

**Cross-cutting security.** A capability architecture: the model reads untrusted page text but holds no tools. Actions are typed, whitelisted and executed by the deterministic layer. Domain allowlist, destructive-action policy, secrets never enter model context.

## 5. The oracle stack: what counts as a bug

A recurring weakness of AI testers is the oracle problem. We answer it with several deterministic oracles of different strength, and we never blur their strength together.

| Class | Oracle | Detects | Example | Proof strength |
| --- | --- | --- | --- | --- |
| A | Hard signals | 5xx from first-party endpoints, uncaught exceptions, first-party console errors above the noise floor | Checkout returns 500 | Strong: no spec needed |
| B | Metamorphic relations | Logic bugs without exact expected values | Filter then clear returns the original list | Strong if the relation was validated first |
| C | Spec claims with provenance | Violations of what the user's description states | A password rule of 8+ characters accepts 4 | Medium: only as good as the quoted sentence |
| D | Cross-layer consistency (UI versus network truth) | Display disagreeing with the app's own API responses | Cart badge shows 3 while the API returns 2 items; shown total differs from the sum of line items | Strong: both values observed, no spec needed |
| E | Temporal differential (this build versus the previous build on the same trace) | Behaviour changes between builds | Same steps now produce a different total | Medium: change is proven, intent is not |

**Relation catalogue (class B).** Sort order is monotonic and stable under repeat; a filter result is a subset of the unfiltered list; a narrower search is a subset of a broader search; the union of pages equals the full list with no duplicates; add then remove returns to the original state; save then reload equals what was saved; list count equals the count badge; create then list shows the item, delete then list hides it; cart total is invariant to insertion order. The LLM binds relations to detected widgets. Each relation is **validated** before use: it must hold across repeated clean runs and on other instances of the same widget, otherwise it is discarded, so an invalid relation cannot produce a false bug.

**Class D is our sleeper advantage.** Most teams will look only at console errors or screenshots. Comparing what the UI shows against what the network returned is deterministic, needs no spec, and catches a whole family of logic bugs that look fine to crash-based tools.

**Tiers shown to users:** VERIFIED (class A or D, replay k of k, shrunk), VERIFIED-VIOLATION (B, C or E, needs intent confirmation), INTERMITTENT (reproduces k of n, rate shown), SUSPECTED, INSUFFICIENT EVIDENCE.

## 6. The proof engine

**Replay.** Each candidate runs in a fresh browser context and a restored world snapshot, k of n times. The result must match the original failure signature.

**Three-valued shrinking.** Classic delta debugging has three outcomes, and so do we: reproduces (FAIL), does not reproduce (PASS), or cannot execute (UNRESOLVED). A reduced trace whose step cannot run because a prerequisite was removed is UNRESOLVED, never PASS. This avoids the most common false conclusion in stateful apps.

**Dependency-aware, hierarchical shrinking.** Level 1: drop steps that produced no state or network change. Level 2: group steps into semantic blocks using data dependencies seen on the tape (the step that creates an entity and the steps that consume it travel together), then run delta debugging over blocks, then inside blocks. Level 3: shrink **values**: numbers toward the smallest triggering value, strings by character-level reduction, so the output can say not only '4 steps' but 'fails with quantity = 0 and a single quote in the name field'.

**Signature locking.** Shrinking must preserve the same failure signature. This stops slippage onto a different, easier bug.

**Speed honesty.** Replays are memoised by subset hash, run in parallel contexts, and use snapshot restore instead of rebuilding. We report measured median replays and shrink time per bug, not a 'seconds' claim.

**Flakiness as a first-class result.** Intermittent bugs are not dropped. Each is replayed repeatedly, reported with its observed rate and an interval, and shrunk with repeated trials per candidate.

**Fix-flip validation.** In ProofBench each planted bug has a fixed variant. A generated test must fail on the buggy build and pass on the fixed one. A test that cannot fail is rejected.

## 7. Uncertainty engine and adaptive testing

**Confidence is composed, not guessed.** Inputs: reproduction rate with interval, oracle class strength, signature stability across replays, distance above the noise floor, relation validation record, and for spec claims whether the quoted sentence is unambiguous.

**Abstention.** When evidence is insufficient the system states INSUFFICIENT EVIDENCE and lists the extra experiment that would resolve it (for example 'replay under throttled network' or 'needs a second account'). Abstaining correctly is scored as a feature, not a failure.

**Calibration as a headline metric.** We measure whether findings labelled high confidence are actually real at the stated rate on ProofBench, and show a reliability diagram. 'When we say high, we are right X of N times' is a claim almost no team will be able to make with data.

**Selective accuracy curve.** Plot precision against the fraction of findings answered. It shows that abstaining on the most uncertain cases buys precision.

**Adaptive testing.** The exploration policy picks the next experiment by expected information gain: where the state graph is thin, where an oracle is uncertain, and where earlier failures cluster. Under equal budgets we compare it to fixed breadth-first and random exploration.

## 8. Adversarial and security lab

A built-in lab that tries to break both the app and the agent.

- **Chaos knobs:** latency, aborted and failed endpoints, offline mode, slow network, clock skew, viewport changes, all logged on the tape so they replay.
- **Hostile inputs:** a curated edge-case input library: empty, very long, unicode and emoji, quotes and angle brackets, zero, negative and huge numbers.
- **Agent traps:** infinite scroll, circular links, dummy pagination, a rotating banner that defeats naive state hashing.
- **Injection pages:** hidden 'ignore previous instructions' text and fake login links. Metric: hijack rate, target 0 of N, against a naive agent that is hijacked.
- **Honeypot decoys:** behaviour that looks like a bug but is intended (a deliberate 404 page, a third-party warning, a slow load). Metric: false positives on decoys.
- **Capability architecture:** reader model without tools, typed actions chosen from a supplied list, egress allowlist, destructive-action policy, and a sandbox-only mode for state-changing operations.

## 9. Digital twin and ProofBench

**App twins.** Conduit (RealWorld), TodoMVC and a purpose-built shop twin with cart, search, filter, sort, pagination, auth and checkout. All run hermetically from containers.

**Bug mutator.** A catalogue of injectable bugs across a taxonomy: hard crash, state-dependent crash (trigger needs k specific steps among distractors), logic bug, validation bug, persistence bug, cross-layer inconsistency, intermittent bug, and decoys. Each bug has a difficulty tier (trigger depth, statefulness, flakiness) and a fixed variant.

**Generated variety.** Bugs and parameters are sampled from a seeded generator, so ProofBench is not a fixed hand-picked list we can overfit. A blind held-out split is generated by a teammate or a hidden seed that nobody tunes against.

**Real-world check.** Run on two or three real open-source apps. Re-introduce a known historical bug where feasible, and report any genuine finding honestly, with the certificate.

**Release.** `proofbench run` is published so judges and others can reproduce our numbers.

## 10. What-if simulator and counterfactual views

- **Counterfactual trace:** for every step in a minimal trace, toggle it off and show the result. Each step is marked necessary or not, with the replay evidence.
- **Value what-if:** change an input value on the tape and see where the failure appears or disappears.
- **Fix what-if:** flip the bug flag and watch the generated test go red to green.
- **Budget what-if:** a plot of expected verified findings against budget, learned from ProofBench runs, so a team can decide how long to run.
- **Blast radius (PR mode):** given a diff or PR description, map touched routes to state-graph nodes and prioritise exploration of affected paths.
- **Counterfactual comparison:** live side by side with a naive ReAct agent and a random monkey on the same app and budget. Every item the baseline files is adjudicated by the certificate checker, so false reports pile up visibly.

## 11. Human review and learning

- Reviewers see a triage queue ordered by value of information, not arrival order.
- Approve: the finding is added to the regression suite and its relation or oracle gains prior weight.
- Reject: a signature-level suppression rule is created, and a re-run shows the finding gone. We measure precision before and after one rejection.
- Review time per finding is recorded, so 'hours saved' can be measured, not assumed.
- Ambiguous classes (B to E) always route to a person before any certificate is described as a defect.

## 12. Delivery: suite, CI and PR mode

- **Regression suite:** successful journeys and certificates export as Playwright tests with role-based locators, fallback locators and a 3 of 3 stability gate.
- **Suite strength:** the suite is scored by mutation testing (percentage of planted bugs it catches) so it is shown to be able to fail.
- **Minimal suite:** set-cover selection of the fewest tests covering the most state-graph edges.
- **CI:** generated GitHub Action; PR comments with certificate links; nightly runs that report new states appeared and behaviour changed (class E).
- **Economics:** after discovery, tests run with no LLM calls. We chart cumulative cost over 100 CI runs against a runtime agent, using our own measured per-bug cost.

## 13. Evaluation plan and claims register

**Metrics (all measured, none predicted):**

| Metric | Meaning |
| --- | --- |
| Precision and recall (deduplicated, bug level) | Correct findings and coverage of planted bugs |
| Certificate validity rate | Share of certificates that `proofqa verify` confirms in a clean container |
| Reproduction rate | Valid replays reproducing the signature |
| Shrink ratio (steps and input size) and replays per shrink | Usefulness and cost of minimisation |
| Time to first verified finding | Speed |
| Cost per verified bug | LLM spend and compute |
| Coverage | States and edges discovered, against reachable ground truth |
| Calibration error and selective accuracy | Whether confidence can be trusted |
| Decoy false-positive rate | Honest precision |
| Injection hijack rate | Agent safety |
| Suite mutation score | Strength of exported tests |
| Review minutes per finding | Human cost |

**Baselines (same app, same step and token budget):** naive ReAct 'find bugs' agent; random monkey clicker; Playwright MCP used as shipped; and our own ablations.

**Ablations:** remove Prove, shrink levels 1 to 3, the state graph, each oracle class, the uncertainty engine and the adaptive policy, one at a time.

**Statistics:** at least 5 seeds per configuration, intervals reported, blind held-out split, tuning only on the dev split.

**Claims register:** every claim on every slide maps to an experiment id and its result. A claim with no experiment is removed or labelled as roadmap.

## 14. The demo (about 4 to 5 minutes)

1. **The race (45 s).** Our agent and a naive agent explore the same app. Two counters run: reports filed and certificates valid. The naive agent's reports pile up; ours are fewer.
2. **The catch (45 s).** A class D bug (cart badge versus API) that console-based tools cannot see, then a state-dependent crash.
3. **The shrink (60 s).** Visual blocks turn red, green and grey as shrinking runs: 31 steps to 4, then values to a minimal input. The counterfactual toggle shows each remaining step is necessary.
4. **Do not trust us (60 s).** A fresh container runs `proofqa verify` on the certificate on screen. Then the generated test goes red on the buggy build and green after the flag flip.
5. **The honest moment (30 s).** On a decoy the system says INSUFFICIENT EVIDENCE and states what experiment it would need. On the injection page it is not hijacked.
6. **Judge's choice (45 s).** A judge picks a bug from a pre-validated menu of about 12 flags and the system finds it. Close on the scoreboard with intervals.

**Fallbacks:** restart and reset the local world; replay a recorded run clearly labelled as recorded; show the verified original trace if shrinking runs out of budget. Never present recorded output as live.

## 15. Where each of the 12 upgrades lives

| # | Upgrade | Role in ProofQA 2.0 |
| --- | --- | --- |
| 1 | AI harness | L0 hermetic runtime plus L9 ProofBench harness |
| 2 | Adversarial testing lab | Section 8 |
| 3 | Independent verification engine | `proofqa verify` and the certificate checker |
| 4 | Scenario replay | Tape, world descriptor, replay anywhere |
| 5 | What-if simulator | Section 10 |
| 6 | Uncertainty engine | Section 7, with abstention and calibration |
| 7 | Evidence explorer | Synchronised timeline of video, network, console, DOM and state-graph node; grounded report sentences link to evidence ids |
| 8 | Automated benchmark suite | ProofBench and the claims register |
| 9 | Human review workflow | Section 11 |
| 10 | Adaptive testing | Information-gain exploration policy |
| 11 | Counterfactual comparison | Live race against baselines, adjudicated by the checker |
| 12 | Digital twin | App twins with the bug mutator |

## 16. Rubric mapping

| Criterion | Where we earn it |
| --- | --- |
| Novelty (20) | Bug Certificate, class D oracle, three-valued hierarchical shrinking with value shrinking, calibrated abstention |
| Feasibility (20) | Deterministic core on Playwright and ddmin; LLM limited to proposals and prose; layered build order |
| Measurable proof (20) | ProofBench, baselines, ablations, calibration, certificate validity rate |
| Demo impact (15) | Race, shrink visual, live independent verification, judge's-choice bug |
| Real-world value (15) | CI and PR mode, mutation-scored suite, zero-LLM replay economics, real OSS runs |
| Defensibility (10) | Honest-limits block, claims register, decoys, security results |

## 17. Likely judge questions

**What is a bug here, and what do you prove?** Reproducible, minimal, signature-stable behaviour violating a stated oracle. We do not claim to prove intent. Classes B to E say so and route to a human.

**Is this just delta debugging plus Playwright?** Those parts are established and we say so. The contribution is the certificate that makes agent output independently checkable, the oracle stack including the cross-layer check, the hierarchical and value shrinking, and calibrated uncertainty, all measured against a generated benchmark.

**What about stateful apps?** World snapshots reset state for every replay, shrinking is dependency-aware, and unexecutable candidates are UNRESOLVED rather than PASS.

**What about intermittent bugs?** Reported as INTERMITTENT with an observed rate, not dropped.

**Why not let the LLM judge or shrink?** It cannot be re-verified. Only executed replays count, and the LLM never holds tools.

**How do you handle false positives from noisy console output?** First-party filtering and a noise floor from an idle visit, plus a decoy set that measures it.

**Is it overfit to your benchmark?** Bugs are generated from a seeded catalogue, tuning uses a dev split, a blind held-out split exists, and real open-source apps are included.

**What if you find nothing?** Coverage and abstention results are still reported. We never invent findings.

## 18. Build order and honesty rules

Everything above is the target architecture. For the live demo the vertical slice must work first, and every other layer must be either working or clearly labelled roadmap:

1. Hermetic app plus tape recorder and signature-matched replay (L0, L4 basics).
2. Certificate builder and the independent `verify` command.
3. Hierarchical shrinking with UNRESOLVED handling.
4. Class A and D oracles, then metamorphic relations with validation.
5. ProofBench with decoys and baselines, so the numbers exist.
6. Uncertainty and calibration, adversarial lab, then dashboard polish.

Honesty rules: only measured numbers appear on slides; recorded runs are labelled; every claim has an experiment id; anything not built is marked roadmap.

## 19. Changes to make in the existing PPT

- Remove leftover drafting notes on the tech-stack and feasibility slides.
- Add a slide defining the Bug Certificate and the proof definition.
- Add a slide for the oracle stack, including the cross-layer check.
- Add a slide for ProofBench, baselines and the calibration claim.
- Add a security and adversarial lab slide with injection and decoy outcomes.
- Replace generic impact text with measured numbers and cited, verified statistics only.
- Add a rubric-mapped summary slide.
