# ProofQA 2.0, Revision 2: The Verification-Native Autonomous QA Engineer

*Team VOID MAIN. VIT Code Apex 3.0, Track 2 (iMocha), problem 02: Autonomous AI QA Engineer. Revision 2, written 12 Oct 2026. Supersedes "ProofQA 2.0: Final Project Context". Sources merged: the PPT (ProofQA), both research reports, the TRACEFORGE dossier, the 12-upgrade list, the Code Apex listing, and a fresh fact-check of outside claims (section 26).*

---

## 0. What changed in this revision

The core idea (Bug Certificates, "do not trust the agent, verify the certificate") is unchanged and is the strongest part of the project. This revision does five things: makes it easier to *understand in 60 seconds* (judges will skim), adds a few cheap-but-memorable features, cuts scope to what can actually be demonstrated live, adds a build plan that fits the real calendar, and tightens every claim so it survives a sceptical jury.

| # | Change | Where |
| --- | --- | --- |
| 1 | Pitch ladder (1 line, 30 s, 2 min) and a verified opening hook | 2 |
| 2 | Judging lens: how the deck wins the four Round 1 criteria; a 3-stage story on top, the ten layers moved to an appendix | 4, 8, 20 |
| 3 | Tamper-evident certificates (hash manifest, TAMPERED verdict, judge-runnable verify) | 6 |
| 4 | New oracle class F (standards and hygiene) so the agent finds real things on unseen apps with zero spec | 9 |
| 5 | Cold-start mode: point at any URL, get certificates | 14 |
| 6 | Certified Fix (find, prove, fix, prove the fix) and Ticket to Certificate, both labelled stretch | 15 |
| 7 | Scope tiers (Tier 0 spine, Tier 1, Tier 2, Roadmap) with honest labels | 17 |
| 8 | Build plan by date, team roles, 24-hour finale plan, rule checks | 18 |
| 9 | Three headline numbers, a Day-0 pilot, `[MEASURE]` placeholders instead of invented figures | 19 |
| 10 | Slide-by-slide PPT blueprint | 20 |
| 11 | Demo v2: judge-run verify, tamper test, optional judge's URL | 21 |
| 12 | Expanded judge Q&A and a risk register | 24, 25 |

**Moved to roadmap by default** (kept in the text, but not promised in the demo): information-gain exploration policy beyond a simple scoring rule, blast-radius PR mode, budget what-if curve, set-cover minimal suite, learning from review rejections, polished evidence explorer, real open-source runs beyond one.

---

## 1. Read first: deadline and triage

The listing is inconsistent about Round 1. The stage timeline shows PPT submission running from 11 Oct 9:00 PM IST to **12 Oct 10:00 AM IST**, while the "important dates" box shows Round 1 on 10 Oct 11:59 PM. Today is 12 Oct. **Confirm the live deadline on Unstop immediately** and watch the VIT Code_Apex 3.0 community on Verzii, where the organisers say updates are posted.

- **If the window is open:** do the under-two-hours list below, in order.
- **If it has closed:** this revision feeds Round 2 (live online evaluation, 16 to 18 Oct) and the finale (24 to 25 Oct).

**Under two hours, in this order:**
1. Delete leftover drafting notes on the tech-stack and feasibility slides.
2. Rewrite slides 1 to 3 using the pitch ladder (section 2) and the blueprint (section 20): thesis, trust problem, one-picture solution.
3. Add the Bug Certificate slide (anatomy plus a `VALID` verify output) and the oracle slide with class D highlighted.
4. Collapse the architecture into the 3-stage picture (Explore, Prove, Deliver). Move the ten layers to an appendix slide.
5. Replace every number you have not measured with either nothing or a label "design goal". Add the verified hook with its source (section 26).
6. Fit everything into the **provided PPT template** (mandatory per the listing). Check its slide limit and section headings before restructuring.

If any time remains: run the Day-0 pilot (section 19) and put the real result on the proof slide.

---

## 2. Pitch ladder and opening hook

**One line.** ProofQA is an autonomous QA engineer whose bug reports are proofs, not opinions: every finding ships as a Bug Certificate that anyone can re-verify in a clean container with one command, without trusting our agent.

**Tagline.** *Do not trust the agent. Verify the certificate.*

**30 seconds.** AI testers write confident bug reports that people have stopped trusting; when curl's maintainers were flooded with low-quality, often AI-generated vulnerability reports, they ended their bug bounty. ProofQA never files an opinion. It explores a web app, proves each suspected bug by replaying it in fresh worlds, shrinks it to the smallest trigger, and issues a certificate that anyone can re-verify with one command. When it is unsure, it says so and names the experiment that would settle it.

**2 minutes (outline).**
1. Problem: opinions, false positives, flaky and un-reproducible output (hook, section 26).
2. Insight: change the unit of output from a report to a checkable proof object.
3. How: detect with deterministic oracles, prove by replay, shrink steps and values, certify.
4. Why believe us: independent verifier, calibrated confidence, abstention, decoys, injection resistance.
5. Proof: ProofBench numbers against baselines (`[MEASURE]`).
6. Value: CI and PR mode, exported tests, zero-LLM replay economics, certified fixes.
7. Close: live `proofqa verify`.

**Language to use consistently** (define each once): *world* (the pinned, replayable environment), *tape* (the recorded run), *oracle* (a deterministic rule that says something is wrong), *certificate*. Use the word **evidence** prominently: the sponsor's own problem statements lean on it (bugs "with evidence", "evidence-based" skills and feedback), and the certificate is evidence-grade QA.

---

## 3. The thesis

Every AI tester today produces an **opinion**: "I think this is a bug." Opinions need trust, and trust is exactly what developers have stopped giving to AI testers (false positives, un-reproducible reports, flaky output).

ProofQA 2.0 changes the unit of output. It does not file bug reports. It issues **Bug Certificates**: self-contained, machine-checkable proof objects that anyone can re-verify in a clean container with one command, without trusting the agent that produced them. "Proof" here is empirical, not mathematical: a recorded, repeatable experiment that anyone can re-run.

Three principles hold the system together:

1. **The agent proposes, the world disposes.** The LLM may suggest actions and draft prose. It never decides whether something is a bug. Browser execution, deterministic oracles and independent re-verification decide.
2. **Every claim is a falsifiable experiment.** Each finding records the hypothesis, the experiment run and the observed outcome. Nothing is asserted that the recorded tape cannot show.
3. **Know what you do not know.** The system calibrates its confidence, abstains when evidence is insufficient, and says which experiment would resolve the doubt.

**What this adds over the original PPT's ProofQA:** a portable and tamper-evident certificate format, a hermetic replay substrate, a cross-layer oracle (UI versus network truth), a standards oracle for unseen apps, two-level shrinking (steps and input values), an uncertainty and abstention engine, an adversarial lab with a generated benchmark (ProofBench), calibrated confidence as a measured result, a counterfactual comparison against baselines, and a cold-start mode for apps we have never seen.

---

## 4. The judging lens (how this wins, honestly)

About 1000 teams are in. Round 1 is a PPT screen on four criteria, so the deck has to be fast to grasp and hard to doubt. Whether shortlisting is per track or global is unknown; assume global.

| Round 1 criterion | What a skimming reviewer looks for | How the deck signals it |
| --- | --- | --- |
| Conceptual clarity | Can I say what this is after 60 seconds? | One-sentence thesis on slide 1, one diagram on slide 3, vocabulary defined once |
| Innovation potential | What is genuinely new, and is the claim honest? | Certificate, class D oracle, value shrinking, calibrated abstention; an explicit "established vs new" box (section 26) |
| Structured problem-solving | Problem, insight, design, validation, plan in order | One question per slide; claims register; tier labels |
| Technical feasibility | Is any of it real? Is the scope sane? | Screenshot of a real `VALID` verify, named stack, deterministic core, LLM limited to proposals, Built/Building/Roadmap labels, pilot numbers |

**Where we expect to differ from most submissions** (an expectation about typical entries, not data): a common Track 2 pattern is an LLM driving Playwright and emitting a bug report with screenshots. We show an artifact that verifies independently, a failure story (abstention, decoys, injection), and measured results or clearly-labelled design goals instead of "saves 70% of QA time" claims.

**Reviewer-skim rules for the deck.**
- Slides 1 to 3 carry the decision. Everything after supports them.
- One claim and one visual per slide; keep body text to a few lines.
- Colour semantics everywhere: green = verified, red = fails, grey = unresolved or abstained.
- Every number carries a tag: `M#` (our experiment id) or `S#` (external source, section 26).
- Show one real artifact (terminal or UI screenshot) before any architecture box.

---

## 5. Problem-statement alignment and sponsor lens

Problem 02 as listed: an AI agent that explores web applications, generates and runs tests, and reports bugs with evidence. **Read the full problem-statement attachment** (not available when this revision was written) and tick off its mandatory deliverables, inputs and any provided target app in a compliance table (appendix slide).

| Problem-statement verb | ProofQA component |
| --- | --- |
| Explores web applications | L1 perception and L2 exploration brain; cold-start mode (section 14) |
| Generates tests | Exported Playwright tests, fix-flip validated, mutation-scored (sections 6.1 and 16) |
| Runs tests | Hermetic runtime (L0), replay k of n, CI Action |
| Reports bugs with evidence | Bug Certificate with evidence bundle; grounded reporter |

**Sponsor angle.** Track 2 problems revolve around assessment-style products with long, stateful, multi-step journeys (candidate journeys, simulations, skill profiles). State-dependent crashes and cross-layer inconsistencies are exactly the bug families that hide in such flows. Use this as an illustration; do not claim knowledge of the sponsor's product.

### 5.1 What we keep, merge and drop

| Source | Keep | Drop or fix |
| --- | --- | --- |
| PPT (ProofQA) | Detect, Prove, Shrink, Test; three oracles; trust tiers; four agents; benchmark with held-out bugs; Bug Lab | "Proof" was never defined precisely; no statefulness handling in ddmin; no uncertainty or security story; leftover drafting notes |
| Landscape report | State-graph coverage, confidence-verified reporting, flakiness and noise concerns | Cross-browser diffing as a core feature |
| Strategy report | Trace minimisation, metamorphic invariants, XPIA security, economics argument, red-team honesty | Falling back to LLM-guessed minimisation |
| TRACEFORGE dossier | Failure signatures, UNRESOLVED and inconclusive handling, claims discipline, three-level demo fallback, harness mindset | Crash-only oracle, optional LLM, no naive-LLM baseline, no calibration |
| 12-upgrade list | All twelve, each with a role (section 22) | None |

---

## 6. The Bug Certificate (the central artifact)

### 6.1 Contents

A certificate is a directory or archive containing:

- **Claim:** one sentence plus the oracle class that supports it (section 9), with provenance (the spec sentence, or the relation name and its validation record).
- **Minimal reproduction:** the shrunk step list and the shrunk input values.
- **Failure signature:** normalised status, endpoint, error type and message, first-party frames. Replays must match this signature, not merely "any failure".
- **Replay record:** k of n fresh-world replays reproduced it, with an interval estimate, plus any intermittency measure.
- **World descriptor:** pinned container image digests, browser version, seed, frozen clock, recorded network, DB snapshot id. This is what makes replay portable.
- **Evidence bundle:** Playwright trace, video, HAR, console log, screenshots, DOM snapshots at each step.
- **Exported test:** a Playwright test that fails on the buggy build and passes on the fixed build where one exists.
- **Honest-limits block:** what the certificate does and does not establish.
- **Integrity manifest (new):** SHA-256 of every file; the certificate id is the hash of the manifest. Optional signature by the issuing key.
- **One-page certificate card (new):** human-readable summary for slides and PR comments.

### 6.2 Verification

`proofqa verify <certificate>` first checks integrity, then rebuilds the world from the descriptor, replays the minimal reproduction in a clean container, and prints one verdict with reasons:

| Verdict | Meaning |
| --- | --- |
| VALID | Integrity intact and the signature reproduced as claimed |
| INVALID | Integrity intact but the failure did not reproduce, or a different signature appeared |
| TAMPERED | Any file differs from the manifest (edit one byte and show it) |
| UNRESOLVED-ENV | The world could not be rebuilt (missing image, version mismatch); never reported as VALID or INVALID |

Design rules for the checker: it shares no code path with the agent; it depends only on the standard library plus Playwright and the container runtime; it is small enough (target a few hundred lines) that a judge can read it; it supports `--json` output and an offline mode that loads bundled image tarballs so it works without internet at the venue.

### 6.3 What a certificate proves

**Proves:** a reproducible, minimal, signature-stable behaviour that violates a stated oracle. **Does not prove:** product intent. Classes B, C, E (and F, which is hygiene) therefore carry an explicit "needs intent confirmation" flag.

---

## 7. Terminology

World = pinned replayable environment. Tape = recorded run (actions, network, console, DOM, state). Oracle = deterministic rule that flags a violation. Signature = normalised failure fingerprint. Block = group of steps linked by data dependencies. These five terms are the only jargon the deck should introduce.

---

## 8. Architecture

### 8.1 The three-stage story (for slides)

**Explore** (find candidates) then **Prove** (replay, shrink, calibrate) then **Deliver** (certificate, exported tests, CI). The ten layers below are the detail for the appendix and for Q&A.

### 8.2 The ten layers

**L0. Hermetic runtime (digital twin and replay substrate).** Target app and dependencies in containers. Controlled time, seeded randomness, recorded and replayable network, copy-on-write database snapshots so every replay starts from the exact same world. Pinned image digests for portability.

**L1. Perception and state.** ARIA-snapshot perception. Normalised state fingerprint (volatile text removed, similarity hashing). Noise-floor calibrator: an idle visit first records pre-existing console and network noise, which is subtracted later. Widget classifier labels lists, search boxes, sort controls, carts, paginators and forms so the right relations can be bound.

**L2. Exploration brain.** The state graph (networkx, persisted) lives outside the LLM. The frontier policy scores candidate actions by novelty, uncertainty and risk. The LLM only proposes semantic actions and form values, and it picks from a numbered list the deterministic layer supplies. It cannot invent URLs or code.

**L3. Oracle stack.** Six oracle families (section 9), each a plug-in, each with a declared proof strength.

**L4. Proof engine.** Fresh-world replay k of n, signature matching, flake estimation, hierarchical shrinking, memoised and parallel replays (section 10).

**L5. Evidence and certificate.** Tape recorder, certificate builder, evidence explorer, and a grounded reporter whose every sentence is checked against the tape.

**L6. Uncertainty and decision.** Confidence composition, abstention, next-best-experiment selection, calibration tracking (section 11).

**L7. Human review and learning.** Review queue ordered by value of information. Reviewer decisions become suppression rules and relation priors (section 16).

**L8. Delivery.** Playwright suite with a mutation-scored strength metric, GitHub Action, PR comment bot, issue export, nightly drift reports.

**L9. Assurance lab (ProofBench).** Bug mutator, generated app twins, adversarial pages, baselines, scoreboard (sections 12, 13).

**Cross-cutting security.** A capability architecture: the model reads untrusted page text but holds no tools. Actions are typed, whitelisted and executed by the deterministic layer. Domain allowlist, destructive-action policy, secrets never enter model context.

### 8.3 Suggested Tier 0 stack (confirm versions before pinning)

Python or TypeScript with Playwright (HAR record and replay, trace viewer, clock control for frozen time); Docker Compose for the world; SQLite file copies for instant database snapshots on the twin; networkx for the state graph; axe-core for class F; a small web dashboard (HTMX or React) for the race and the shrink visual; an LLM behind a thin interface with response caching so the deterministic core still runs when the model is slow or offline.

---

## 9. The oracle stack: what counts as a bug

A recurring weakness of AI testers is the oracle problem. We answer it with several deterministic oracles of different strength, and we never blur their strength together.

| Class | Oracle | Detects | Example | Proof strength |
| --- | --- | --- | --- | --- |
| A | Hard signals | 5xx from first-party endpoints, uncaught exceptions, first-party console errors above the noise floor | Checkout returns 500 | Strong: no spec needed |
| B | Metamorphic relations | Logic bugs without exact expected values | Filter then clear returns the original list | Strong if the relation was validated first |
| C | Spec claims with provenance | Violations of what the user's description states | A password rule of 8+ characters accepts 4 | Medium: only as good as the quoted sentence |
| D | Cross-layer consistency (UI versus network truth) | Display disagreeing with the app's own API responses | Cart badge shows 3 while the API returns 2 items; shown total differs from the sum of line items | Strong: both values observed, no spec needed |
| E | Temporal differential (this build versus the previous build on the same trace) | Behaviour changes between builds | Same steps now produce a different total | Medium: change is proven, intent is not |
| **F (new)** | Standards and hygiene | Violations of published rules: accessibility (axe-core), broken first-party links or assets, mixed content, console security-policy violations, unlabeled form fields | Checkout button has no accessible name; product image returns 404 | Strong that the rule is broken; low to medium severity; intent not at issue |

**Why class F.** On an app we have never seen, classes B and C need setup and A needs a crash. F gives zero-spec breadth quickly, so the cold-start demo (section 14) finds real things. It is reported in its own HYGIENE tier and excluded from the functional-bug precision metric, so it cannot dilute the numbers or be accused of padding.

**Relation catalogue (class B).** Sort order is monotonic and stable under repeat; a filter result is a subset of the unfiltered list; a narrower search is a subset of a broader search; the union of pages equals the full list with no duplicates; add then remove returns to the original state; save then reload equals what was saved; list count equals the count badge; create then list shows the item, delete then list hides it; cart total is invariant to insertion order. The LLM binds relations to detected widgets. Each relation is **validated** before use: it must hold across repeated clean runs and on other instances of the same widget, otherwise it is discarded, so an invalid relation cannot produce a false bug.

**Class D is our sleeper advantage.** Most teams will look only at console errors or screenshots. Comparing what the UI shows against what the network returned is deterministic, needs no spec, and catches a whole family of logic bugs that look fine to crash-based tools.

**Tiers shown to users:** VERIFIED (class A or D, replay k of k, shrunk), VERIFIED-VIOLATION (B, C or E, needs intent confirmation), HYGIENE (F), INTERMITTENT (reproduces k of n, rate shown), SUSPECTED, INSUFFICIENT EVIDENCE.

---

## 10. The proof engine

**Replay.** Each candidate runs in a fresh browser context and a restored world snapshot, k of n times. The result must match the original failure signature.

**Three-valued shrinking.** Classic delta debugging has three outcomes, and so do we: reproduces (FAIL), does not reproduce (PASS), or cannot execute (UNRESOLVED). A reduced trace whose step cannot run because a prerequisite was removed is UNRESOLVED, never PASS. This avoids the most common false conclusion in stateful apps.

**Dependency-aware, hierarchical shrinking.** Level 1: drop steps that produced no state or network change. Level 2: group steps into semantic blocks using data dependencies seen on the tape (the step that creates an entity and the steps that consume it travel together), then run delta debugging over blocks, then inside blocks. Level 3: shrink **values**: numbers toward the smallest triggering value, strings by character-level reduction, so the output can say not only "4 steps" but "fails with quantity = 0 and a single quote in the name field".

**Signature locking.** Shrinking must preserve the same failure signature. This stops slippage onto a different, easier bug.

**Speed honesty.** Replays are memoised by subset hash, run in parallel contexts, and use snapshot restore instead of rebuilding. We report measured median replays and shrink time per bug, not a "seconds" claim.

**Flakiness as a first-class result.** Intermittent bugs are not dropped. Each is replayed repeatedly, reported with its observed rate and an interval, and shrunk with repeated trials per candidate. (Context: flakiness is a documented, large-scale problem; see section 26.)

**Fix-flip validation.** In ProofBench each planted bug has a fixed variant. A generated test must fail on the buggy build and pass on the fixed one. A test that cannot fail is rejected.

---

## 11. Uncertainty engine and adaptive testing

**Confidence is composed, not guessed.** Inputs: reproduction rate with interval, oracle class strength, signature stability across replays, distance above the noise floor, relation validation record, and for spec claims whether the quoted sentence is unambiguous.

**Abstention.** When evidence is insufficient the system states INSUFFICIENT EVIDENCE and lists the extra experiment that would resolve it (for example "replay under throttled network" or "needs a second account"). Abstaining correctly is scored as a feature, not a failure.

**Calibration as a headline metric.** We measure whether findings labelled high confidence are actually real at the stated rate on ProofBench, and show a reliability diagram. "When we say high, we are right X of N times" is a claim few teams will be able to make with data.

**Selective accuracy curve.** Plot precision against the fraction of findings answered. It shows that abstaining on the most uncertain cases buys precision.

**Adaptive testing (Tier 2).** Tier 0 and 1 use a simple scoring rule (novelty, uncertainty, risk). The full information-gain policy (state graph thin spots, oracle uncertainty, failure clusters) is a stretch; under equal budgets it would be compared to breadth-first and random exploration. Do not present it as built until it is.

---

## 12. Adversarial and security lab

A built-in lab that tries to break both the app and the agent.

- **Chaos knobs:** latency, aborted and failed endpoints, offline mode, slow network, clock skew, viewport changes, all logged on the tape so they replay.
- **Hostile inputs:** a curated edge-case input library: empty, very long, unicode and emoji, quotes and angle brackets, zero, negative and huge numbers.
- **Agent traps:** infinite scroll, circular links, dummy pagination, a rotating banner that defeats naive state hashing.
- **Injection pages:** hidden "ignore previous instructions" text and fake login links. Metric: hijack rate, target 0 of N, against a naive agent that is hijacked.
- **Honeypot decoys:** behaviour that looks like a bug but is intended (a deliberate 404 page, a third-party warning, a slow load). Metric: false positives on decoys.
- **Capability architecture:** reader model without tools, typed actions chosen from a supplied list, egress allowlist, destructive-action policy, and a sandbox-only mode for state-changing operations.

---

## 13. Digital twin and ProofBench

**App twins.** Conduit (RealWorld), TodoMVC and a purpose-built shop twin with cart, search, filter, sort, pagination, auth and checkout. All run hermetically from containers. The shop twin is the Tier 0 priority.

**Bug mutator.** A catalogue of injectable bugs across a taxonomy: hard crash, state-dependent crash (trigger needs k specific steps among distractors), logic bug, validation bug, persistence bug, cross-layer inconsistency, intermittent bug, hygiene issue, and decoys. Each bug has a difficulty tier (trigger depth, statefulness, flakiness) and a fixed variant.

**Generated variety.** Bugs and parameters are sampled from a seeded generator, so ProofBench is not a fixed hand-picked list we can overfit. A blind held-out split is generated by a teammate or a hidden seed that nobody tunes against.

**Real-world check.** Run on one to three real open-source apps. Re-introduce a known historical bug where feasible, and report any genuine finding honestly, with the certificate.

**Release.** `proofbench run` is published so judges and others can reproduce our numbers.

---

## 14. Cold-start mode: any URL, zero configuration (new)

**Why.** Finale-style evaluation commonly involves an app the team has not seen. The twins prove the method; cold-start proves it is not a trick. (Assumption: the finale may hand us a target; confirm with the organisers.)

**Behaviour.** Input is a URL, optional credentials, an allowlist scope and a time budget. Default is safe mode: non-destructive actions only; state-changing actions need an explicit sandbox flag. Without any spec the system can raise classes A, D and F, and class B where widgets are recognised. "Found nothing, here is the coverage" is a valid result.

**Requirements.** Handle cookie banners, login forms with supplied credentials, SPA routing, shadow DOM and same-origin iframes. Out of scope and stated as such: canvas-only apps, native mobile, CAPTCHAs, third-party iframes.

**Measure.** Time to first certificate on at least five unseen apps (mix of open-source demo apps); report median and range, including runs with no finding.

**Rehearsal rule.** Before the finale, run cold-start on at least five apps nobody on the team has tuned for. Fix perception failures found there, not on the twins.

---

## 15. Certified Fix and Ticket to Certificate (stretch, new)

### 15.1 Certified Fix (proof-carrying patch)

Closes the loop: find, prove, fix, **prove the fix**. Applies where source is available (twins, open-source targets, PR mode).

1. Input: a VALID certificate and read-only access to the source in a sandbox.
2. An LLM proposes a patch as a diff. It decides nothing.
3. A deterministic gate runs: (a) the certificate now replays INVALID on the patched build, (b) the exported regression suite and prior certificates stay green, (c) a fixed-budget re-exploration yields no new failure signature, (d) the patch stays within a size and scope limit and does not merely swallow the error.
4. Output: FIX-VERIFIED with the evidence, or FIX-REJECTED with the failing gate.

**Metrics.** Verified-fix rate on ProofBench; false-fix rate (patch masks the bug, caught by the held-out variant test) versus an ungated LLM-patch baseline.

**Label.** Stretch. Show it only if it works live; otherwise roadmap.

### 15.2 Ticket to Certificate

Input: a free-text bug ticket. The agent hypothesises steps, runs them in the world, and returns either a certificate or a **certified non-reproduction** ("not reproduced in N fresh-world attempts; experiments tried: ..."). The second output is rare and useful: it tells triage why a ticket stalled. Label: stretch.

---

## 16. What-if simulator, human review, delivery

**What-if and counterfactuals.**
- Counterfactual trace: for every step in a minimal trace, toggle it off and show the result; each step is marked necessary or not with replay evidence.
- Value what-if: change an input on the tape and see where the failure appears or disappears.
- Fix what-if: flip the bug flag and watch the generated test go red to green.
- Counterfactual comparison: live side by side with a naive ReAct agent and a random monkey on the same app and budget; every item the baseline files is adjudicated by the certificate checker, so false reports pile up visibly.
- Roadmap: budget what-if curve; blast radius for PR mode (map a diff to state-graph nodes and prioritise affected paths).

**Human review and learning.**
- Reviewers see a triage queue ordered by value of information, not arrival order.
- Approve: finding joins the regression suite and its oracle gains prior weight.
- Reject: a signature-level suppression rule is created; a re-run shows the finding gone. Measure precision before and after one rejection.
- Review time per finding is recorded, so "hours saved" is measured, not assumed.
- Ambiguous classes (B, C, E, F) always route to a person before any certificate is described as a defect.

**Delivery.**
- Regression suite: successful journeys and certificates export as Playwright tests with role-based locators, fallback locators and a 3 of 3 stability gate.
- Suite strength: scored by mutation testing (share of planted bugs it catches).
- CI: generated GitHub Action; PR comments with certificate cards; nightly runs reporting new states and behaviour changes (class E).
- Economics: after discovery, tests run with no LLM calls; chart cumulative cost over 100 CI runs against a runtime agent, using our own measured per-bug cost.
- Roadmap: set-cover minimal suite.

---

## 17. Scope tiers and honesty labels

Everything in this file is the target architecture. Every item on a slide must carry one label: **Built**, **Building**, or **Roadmap**. Nothing is shown as Built until it ran.

| Tier | Must exist by | Contents |
| --- | --- | --- |
| **Tier 0: the demo spine** | Round 2 live evaluation (16 Oct) as far as possible; certainly by the finale | Shop twin with at least 6 planted bugs including one class D, one state-dependent crash and one decoy; tape recorder; replay k of n with signature matching; certificate builder with integrity manifest; independent `proofqa verify` (VALID, INVALID, TAMPERED); steps-level shrinking (levels 1 and 2) with UNRESOLVED handling; classes A and D; naive ReAct baseline; the race dashboard |
| **Tier 1** | Finale | Value shrinking; class B with relation validation (start with four relations: filter subset, sort monotonic, list count equals badge, add then remove); class F via axe-core; uncertainty tiers and abstention on the decoy; injection page; Playwright export with fix-flip; seeded ProofBench generator (about 20 bugs) with decoys; cold-start mode |
| **Tier 2 (stretch)** | Only if Tier 0 and 1 are solid | Certified Fix; Ticket to Certificate; calibration reliability diagram over 5 seeds; one real open-source run; evidence explorer polish; PR mode |
| **Roadmap** | Slides only, labelled | Information-gain policy; review-queue learning; budget what-if; set-cover suite; nightly drift reports; mobile and canvas support |

---

## 18. Build plan, roles and the 24-hour finale

### 18.1 Calendar (2026)

| Date | Event | Plan |
| --- | --- | --- |
| Mon 12 Oct | Round 1 PPT closes (confirm time) | Submit the revised deck; repo skeleton; shop twin started |
| Wed 14 Oct | Round 1 results | Tier 0 build continues regardless of outcome |
| 15 to 17 Oct | Build days | Tape, replay, certificate, verify, shrinking L1 and L2, classes A and D, naive baseline; Day-0 pilot; record a 2-minute demo clearly labelled as recorded |
| Fri 16 to Sun 18 Oct | Round 2: live online PPT evaluation | Present deck v2 with real pilot numbers; slot time unknown, prepare early |
| Mon 19 Oct | Round 2 results | |
| 19 to 23 Oct | Tier 1 and rehearsal | Value shrinking, class B, class F, abstention, injection page, export, cold-start on 5 unseen apps; offline fallbacks; pre-pull images |
| Sat 24 to Sun 25 Oct | 24-hour on-campus finale at VIT Pune | See 18.3 |

### 18.2 Roles (assumes four members; merge roles if fewer and drop to Tier 0 plus the cold-start rehearsal)

1. **Runtime and replay lead:** L0, tape, snapshots, signature matching, certificate format, `verify`.
2. **Agent and oracle lead:** L1 to L3, state graph, classes A, D, F, B, cold-start adapters.
3. **Proof and benchmark lead:** shrinking, ProofBench mutator, baselines, statistics, calibration, claims register.
4. **Product and story lead:** dashboard and race UI, evidence view, PPT, demo script, rehearsals, Q&A drilling.

### 18.3 The 24-hour finale

**Rule check first.** The listing says finalists "build and implement their proposed solution" during the 24 hours. **Ask the organisers (Unstop or the Verzii community) what pre-existing code is allowed.** Until answered, plan for both cases: (a) pre-built code allowed: arrive with Tier 0 and Tier 1 ready and spend the 24 hours on cold-start, hardening and the stretch items; (b) only open-source libraries and prior design allowed: keep Tier 0 as small, well-understood scripts that can be rebuilt in roughly the first third of the window, and have the design, bug catalogue and benchmark plan ready on paper.

**Indicative hour plan.** H0 to 2: environment, re-validate the pipeline, read the target if one is provided. H2 to 12: build or extend, run cold-start on the target, fix perception failures. H12 to 18: benchmark run, certificates, polish. H18: **feature freeze**. H18 to 22: rehearsals with a timer, fallback drills. H22 to 24: buffer and sleep.

**Logistics checklist.** Images pre-pulled and saved as tarballs; offline verify tested; cached LLM responses for the demo path; hotspot; chargers; a second laptop with the same setup; recorded fallback video labelled as recorded.

---

## 19. Evaluation plan, Day-0 pilot and claims register

### 19.1 Three headline numbers (the ones on slide 10)

1. **Certificate validity rate:** share of certificates that `proofqa verify` confirms in a clean container.
2. **False reports per run versus baseline:** same app, same step and token budget, adjudicated by the checker.
3. **Shrink ratio:** median steps before and after, and input size before and after.

Calibration error and selective accuracy are the "bonus" fourth result once enough seeds exist.

### 19.2 Day-0 pilot (smallest honest experiment)

Shop twin with 5 planted bugs and 2 decoys. Configurations: naive ReAct baseline versus ProofQA Tier 0. Three seeds each. Record reports filed, certificates valid, false positives, time to first valid certificate. Even this small chart gives slide 10 a real result. Label it "pilot, 3 seeds". If it cannot be run before submission, slide 10 shows the experiment design and states "results reported at Round 2". **Never fill the chart with invented numbers.**

Placeholder format for any number not yet measured: `[MEASURE: metric, experiment id]`.

### 19.3 Full metrics (all measured, none predicted)

| Metric | Meaning |
| --- | --- |
| Precision and recall (deduplicated, bug level) | Correct findings and coverage of planted bugs |
| Certificate validity rate | Share of certificates that `proofqa verify` confirms in a clean container |
| Reproduction rate | Valid replays reproducing the signature |
| Shrink ratio (steps and input size) and replays per shrink | Usefulness and cost of minimisation |
| Time to first verified finding and to first certificate on unseen apps | Speed, including cold-start |
| Cost per verified bug | LLM spend and compute |
| Coverage | States and edges discovered against reachable ground truth |
| Calibration error and selective accuracy | Whether confidence can be trusted |
| Decoy false-positive rate | Honest precision |
| Injection hijack rate | Agent safety |
| Suite mutation score | Strength of exported tests |
| Review minutes per finding | Human cost |
| Verified-fix rate and false-fix rate (stretch) | Certified Fix quality |

**Baselines (same app, same step and token budget):** naive ReAct "find bugs" agent; random monkey clicker; Playwright MCP used as shipped; our own ablations. If time allows, also run Playwright's own planner and generator agents as a baseline and say exactly what was compared.

**Ablations:** remove Prove, shrink levels 1 to 3, the state graph, each oracle class, the uncertainty engine and the adaptive policy, one at a time.

**Statistics:** at least 5 seeds per configuration for final numbers, intervals reported (for proportions use a Wilson interval), blind held-out split, tuning only on the dev split.

**Claims register:** every claim on every slide maps to an experiment id and its result. A claim with no experiment is removed or labelled Roadmap.

---

## 20. PPT blueprint (map into the provided template)

Target: 12 main slides plus an appendix. Adapt to the template's required sections and slide limit; if the template forces a different order, keep the logic and the first-three-slides rule.

| # | Slide | Headline (one sentence) | Visual | Evidence tag |
| --- | --- | --- | --- | --- |
| 1 | Title | ProofQA: bug reports that prove themselves | Logo, tagline, team, Track 2 problem 02 | none |
| 2 | The trust problem | AI testers file opinions, and people have stopped believing them | One striking fact and a diagram of "opinion vs proof" | S1 (curl), S2 (flakiness) |
| 3 | Our answer | Detect, prove, shrink, certify, then anyone can verify | Single horizontal flow with a certificate card at the end | none |
| 4 | The Bug Certificate | A certificate is a self-contained proof object, re-verifiable with one command | Anatomy diagram and a real `VALID` terminal screenshot | M1 |
| 5 | How it works | Explore, Prove, Deliver; the LLM proposes, the world decides | 3-stage diagram, LLM drawn with no tools | none |
| 6 | What counts as a bug | Six deterministic oracles with declared strength; the cross-layer check needs no spec | Table with class D example (badge 3 vs API 2) | M2 |
| 7 | Shrinking | From a 31-step run to a 4-step trigger and a minimal input (illustrative until measured) | Red, green, grey block animation or still | M3 |
| 8 | Know what you do not know | Calibrated confidence and abstention: when we say high, we are right X of N | Reliability diagram or abstention example | M4 (or "Building") |
| 9 | Safety and adversarial lab | The model reads untrusted pages but holds no tools; decoys and injection are measured | Capability diagram, hijack and decoy results | M5 |
| 10 | Proof | Against baselines on the same budget: validity, false reports, shrink ratio | Bar chart with intervals from the pilot | M1 to M3 |
| 11 | Real-world value | CI and PR comments, exported tests with zero-LLM replay, certified fixes | CI flow, cost-over-runs chart (measured) | M6 |
| 12 | Feasibility, plan and why us | Vertical slice status, stack, timeline to finale, risks, and the four Round 1 criteria in one table | Built, Building, Roadmap chips; calendar strip | none |
| A1 | Full architecture (ten layers) | | Layer diagram | |
| A2 | Relation catalogue and ProofBench taxonomy | | Tables | |
| A3 | Claims register | | Table | |
| A4 | Problem-statement compliance | | Table | |
| A5 | Prior art and what is established vs new | | Table (section 26) | |

**Slide rules.** Every slide ends with a so-what. No unmeasured numbers. No drafting notes. External facts carry a source tag. Use the same colour semantics throughout.

**"Established vs new" box (appendix, and one line on slide 5).** Established: delta debugging, metamorphic testing, property-based shrinking, Playwright. New in combination: the portable, tamper-evident certificate with independent verification; the cross-layer oracle; dependency-aware hierarchical and value shrinking with three-valued results; calibrated abstention measured on a generated benchmark.

---

## 21. The demo (about 5 minutes) and Round 2 delivery

### 21.1 Core script

1. **The race (45 s).** Our agent and a naive agent explore the same app. Three counters run: reports filed, certificates valid, false reports. The naive agent's reports pile up; ours are fewer and all verify.
2. **The catch (45 s).** A class D bug (cart badge versus API) that console-based tools cannot see, then a state-dependent crash.
3. **The shrink (60 s).** Visual blocks turn red, green and grey as shrinking runs: steps shrink, then values shrink to a minimal input. The counterfactual toggle shows each remaining step is necessary.
4. **Do not trust us (60 s).** A judge, or the presenter handing over the keyboard, runs `proofqa verify` on the certificate in a fresh container: VALID. Then **edit one byte** and run it again: TAMPERED. Then the generated test goes red on the buggy build and green after the flag flip.
5. **The honest moment (30 s).** On a decoy the system says INSUFFICIENT EVIDENCE and states the experiment it would need. On the injection page it is not hijacked.
6. **Judge's choice (45 s).** A judge picks a bug from a pre-validated menu of about 12 flags and the system finds it. **Optional bonus:** a judge names a URL and cold-start runs under a hard time cap; if it finds nothing, show the coverage and the abstention, which is still a good outcome.
7. **Close (15 s).** Scoreboard with intervals; if built, one Certified Fix gate result.

If time is short, cut in this order: Certified Fix, judge's URL, injection, judge's choice. Never cut steps 3 and 4.

### 21.2 Round 2 (live online PPT evaluation)

Plan roughly: a tight deck walk of slides 1 to 6 and 10, a short recorded demo clearly labelled as recorded (or a live `verify` if screen-sharing allows), then Q&A. Prepare the 30-second pitch, the 2-minute version and a "one slide only" version in case the slot is shorter than announced.

### 21.3 Fallbacks

Restart and reset the local world; replay a recorded run clearly labelled as recorded; show the verified original trace if shrinking runs out of budget; if the LLM is unavailable, run the demo path from cached proposals and say so. Never present recorded output as live.

---

## 22. Where each of the 12 upgrades lives

| # | Upgrade | Role in ProofQA 2.0 |
| --- | --- | --- |
| 1 | AI harness | L0 hermetic runtime plus L9 ProofBench harness |
| 2 | Adversarial testing lab | Section 12 |
| 3 | Independent verification engine | `proofqa verify` and the certificate checker (section 6.2) |
| 4 | Scenario replay | Tape, world descriptor, replay anywhere |
| 5 | What-if simulator | Section 16 |
| 6 | Uncertainty engine | Section 11, with abstention and calibration |
| 7 | Evidence explorer | Synchronised timeline of video, network, console, DOM and state-graph node; grounded report sentences link to evidence ids (polish is Tier 2) |
| 8 | Automated benchmark suite | ProofBench and the claims register |
| 9 | Human review workflow | Section 16 |
| 10 | Adaptive testing | Simple scoring rule in Tier 0 and 1; information-gain policy is Tier 2 |
| 11 | Counterfactual comparison | Live race against baselines, adjudicated by the checker |
| 12 | Digital twin | App twins with the bug mutator |

---

## 23. Rubric mapping

**Track rubric (from the earlier context file).**

| Criterion | Where we earn it |
| --- | --- |
| Novelty (20) | Bug Certificate with integrity and independent verify, class D oracle, three-valued hierarchical shrinking with value shrinking, calibrated abstention |
| Feasibility (20) | Deterministic core on Playwright and ddmin; LLM limited to proposals and prose; tiered build order; cold-start rehearsal |
| Measurable proof (20) | ProofBench, baselines, ablations, calibration, certificate validity rate, Day-0 pilot |
| Demo impact (15) | Race, shrink visual, judge-run verify and tamper test, judge's-choice bug |
| Real-world value (15) | CI and PR mode, mutation-scored suite, zero-LLM replay economics, Certified Fix (stretch) |
| Defensibility (10) | Honest-limits block, claims register, decoys, security results, scope labels |

**Round 1 criteria** are mapped in section 4.

---

## 24. Likely judge questions

**What is a bug here, and what do you prove?** Reproducible, minimal, signature-stable behaviour violating a stated oracle. We do not claim to prove intent. Classes B, C, E and F say so and route to a human.

**Is this just delta debugging plus Playwright?** Those parts are established and we say so. The contribution is the certificate that makes agent output independently checkable, the oracle stack including the cross-layer check, hierarchical and value shrinking, and calibrated uncertainty, all measured against a generated benchmark.

**How is this different from Playwright's own Test Agents and other AI QA tools?** Playwright's planner, generator and healer explore an app, write tests and repair failing ones. That is test authoring and maintenance. ProofQA adjudicates defects: it produces independently verifiable, minimal, tamper-evident evidence and measures its own false-report and calibration rates. We build on Playwright and the two are complementary. (Source: section 26. Do not claim comparison results unless we ran them.)

**What about stateful apps?** World snapshots reset state for every replay, shrinking is dependency-aware, and unexecutable candidates are UNRESOLVED rather than PASS.

**What about intermittent bugs?** Reported as INTERMITTENT with an observed rate and an interval, not dropped.

**Why not let the LLM judge or shrink?** It cannot be re-verified. Only executed replays count, and the LLM never holds tools.

**How do you handle false positives from noisy console output?** First-party filtering and a noise floor from an idle visit, plus a decoy set that measures it.

**Is it overfit to your benchmark?** Bugs are generated from a seeded catalogue, tuning uses a dev split, a blind held-out split exists, cold-start is tested on apps nobody tuned for, and real open-source apps are included.

**What if you find nothing?** Coverage and abstention results are still reported. We never invent findings.

**Is `verify` really independent?** It shares no code path with the agent, has a small auditable codebase, checks integrity first, and runs from the certificate alone in a clean container, offline if needed.

**What does it cost and how slow is it?** The LLM only proposes; replays and exported tests run with no LLM calls. We report measured cost per verified bug and median replays per shrink, not estimates.

**What about login, CAPTCHAs, third-party widgets, canvas and mobile?** Login with supplied credentials is supported; CAPTCHAs, third-party iframes, canvas-only apps and native mobile are out of scope and listed as roadmap.

**Is it safe to point at a real site?** Safe mode is the default: allowlisted domains, non-destructive actions, secrets never reach the model, and state-changing actions need an explicit sandbox flag.

**Why would a company adopt it?** Because triage time is the cost: every finding arrives with a minimal reproduction and an independent verdict, and regression tests run without LLM spend. (Quantify only with our measured review minutes per finding.)

---

## 25. Risk register

| Risk | Mitigation |
| --- | --- |
| Over-scope; half-built layers | Tier labels; Tier 0 first; feature freeze at H18 of the finale |
| Deck too dense for a skimming reviewer | Pitch ladder; 3-stage story; ten layers in the appendix; first-three-slides rule |
| Live demo fails | Fallbacks in 21.3; recorded run labelled; reset script |
| Judge's machine or venue network issues | Offline verify with bundled image tarballs; second laptop; hotspot |
| LLM latency, rate limits or outage | Response caching; deterministic core runs on cached proposals; say so openly |
| Unknown target app breaks perception | Cold-start rehearsal on five unseen apps; safe mode; "found nothing" handled gracefully |
| Overclaiming | Claims register; `[MEASURE]` placeholders; Built, Building, Roadmap labels |
| Unclear rules on pre-built code | Ask the organisers now; dual plan in 18.3 |
| Template or deadline surprises | Confirm on Unstop; follow the Verzii community for updates |
| Many similar "LLM plus Playwright" entries | Differentiate on the certificate, independent verify and measured honesty |
| Fatigue during the 24 hours | Hour plan, freeze time, sleep buffer, role clarity |

---

## 26. Verified external facts and prior art

Checked on 12 Oct 2026. Use the wording style below, keep the source on the slide, and re-check before printing anything beyond it.

| Id | Fact (safe wording) | Source | Caveat |
| --- | --- | --- | --- |
| S1 | The curl project ended its bug bounty at the end of January 2026 after a surge of low-quality, often AI-generated vulnerability reports | BleepingComputer; The Register (21 Jan 2026); heise | These were security reports, not QA test reports. Present as evidence of the trust problem, not as a QA statistic |
| S2 | At Google, about 1.5% of test runs gave flaky results and almost 16% of tests had some flakiness; large tests were flaky far more often than small ones (14% versus 0.5% in one week) | Google Testing Blog, May 2016 and April 2017 | Google's internal corpus, dated; say so |
| S3 | Playwright ships three Test Agents (planner, generator, healer) since v1.56 (October 2025); the planner explores an app and writes a Markdown plan, the generator turns it into tests, the healer repairs failing tests and may skip a test it believes is genuinely broken | Playwright documentation (Test Agents) | Position as complementary substrate and baseline, not a rival |

**Do not use** other statistics (for example industry-wide cost-of-bugs figures) unless the source is re-checked and cited.

**Prior art to credit** (confirm exact citations before printing): delta debugging (Zeller and Hildebrandt, IEEE TSE, 2002); metamorphic testing (T. Y. Chen and colleagues, late 1990s); proof-carrying code (Necula, POPL 1997), the inspiration for certificates that carry their own checkable evidence; property-based testing and shrinking (QuickCheck, Hypothesis); mutation testing; Playwright.

---

## 27. Honesty rules

- Only measured numbers appear on slides; targets are labelled "design goal"; unmeasured slots show `[MEASURE]` until filled.
- Recorded runs are labelled as recorded; live means live.
- Every claim has an experiment id (`M#`) or a source id (`S#`).
- Anything not built is marked Roadmap; anything in progress is marked Building.
- A certificate states what it does not prove.
- If the system finds nothing, it reports coverage and says so.
