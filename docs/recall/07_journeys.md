# Prompt 7: Intent Journeys and Mutation Engine Report

## 1. Decision Gate Analysis
- **Gate Check**: Performed evaluation on `results/recall/rules_probes_goexplore/funnel.json`.
- **Finding**: B02 reached S1 in 0/10 seeds (< 70% threshold).
- **Decision**: Activation of generic intent journey planner and journey mutation engine (`IF STUCK` branch).

## 2. Implementation Overview
- `proofqa/explore/journeys.py`:
  - **Intent Vocabulary**: 12 generic commerce and CRUD intents (`add_item`, `remove_item`, `apply_code`, `clear_code`, `checkout`, `register`, `login`, `update_profile`, `search`, `sort`, `filter`, `paginate`).
  - **Lexicon Grounding**: Grounding through keyword matchers defined in `docs/recall/lexicon.md`.
  - **Mutation Operators**:
    - `delete`: removes random step while preserving minimal sequence.
    - `swap`: transposes adjacent intents to explore order permutations.
    - `repeat`: duplicates an action (e.g. repeated item adds).
    - `insert_inverse`: inserts inverse counterpart (e.g. `add_item` -> `remove_item`, `apply_code` -> `clear_code`).
  - **Choke Point Guarantee**: All journey proposals are dispatched strictly through `ground_action()`. Unmapped intents are skipped safely.

## 3. Verification
- Deterministic mutations and intent mappings verified via `tests/test_prompt7_journeys.py`.
- Zero hardcoded bug IDs or selectors.
