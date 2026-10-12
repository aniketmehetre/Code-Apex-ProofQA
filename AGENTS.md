# ProofQA 2.0 agent rules
Read docs/CONTEXT.md before any task. It is the source of truth for scope, vocabulary and honesty rules.

## Non-negotiable architecture rules
1. The LLM never decides whether something is a bug. Detection, replay, shrinking, certification and verification are deterministic code.
2. proofqa.proof, proofqa.cert and proofqa.oracles must never import proofqa.llm. Keep the import-guard test passing.
3. proofqa/cert/verify.py must not import proofqa.explore, proofqa.oracles, proofqa.llm or proofqa.uncertainty.
4. The tape is the single source of truth for what happened. Replay, shrinking, certificate and evidence are all derived from it.
5. A replay has three outcomes: FAIL (target signature observed), PASS (ran fully, signature not observed), UNRESOLVED (could not execute). UNRESOLVED is never treated as PASS.
6. Shrinking must preserve the same failure signature, not just any failure.
7. Everything works with OFFLINE=1 (no API key). The LLM only proposes actions, form values, claim extraction and report prose.
8. Contracts in proofqa/contracts.py are frozen after Prompt 0.2. Change them only after adding a note to docs/progress.md.

## Engineering rules
- Python 3.12, type hints everywhere, Pydantic v2 models at every boundary, async Playwright, ruff clean.
- Write the test first or alongside it. No feature is done without a passing test and a runnable command.
- Prefer the standard library and dependencies already in pyproject.toml. Ask before adding a dependency.
- No secrets in code, tapes or certificates. Read keys from env only.
- Do not invent numbers. Any metric shown anywhere must come from a bench run and be recorded in docs/claims.md.
- Never present recorded output as live. Label recorded runs.

## Definition of done for every task
Run make lint and make test. Append what changed, what is untested and any risk to docs/progress.md. State exactly which commands to run to see it work.
