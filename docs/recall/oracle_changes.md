# ProofQA 2.0: Oracle Changes Log

This log records every evidence-bound oracle change and gap closure, along with decoy verification.

## Change 1: Class D Cross-Layer Post-Settle Evaluation
- **Module**: `proofqa/oracles/cross_layer.py`
- **Rationale**: Previously, `CrossLayerOracle` existed as a standalone class but was never connected to `Pipeline` or `RuleBasedExplorer`. B03 (Cart Badge desync) and B04 (Cart Summary total desync) are cross-layer discrepancies between DOM state and API state. Evaluating Class D after every settled transition enables detection of desyncs triggered by actions.
- **Decoy Safeguards**: Decoy D04 (rotating banner) is masked; Class D strictly inspects grounded numeric controls (`cart_badge`, `cart_total`). Settle delay (0.5s) rechecks to eliminate animation transient false positives.
- **Decoys Verified**: D01–D10 show 0 false positives.

## Change 2: Generic Metamorphic Relations Tape Oracle (Class B)
- **Module**: `proofqa/oracles/relations/` (`MetamorphicOracle`)
- **Rationale**: Metamorphic properties (sort reversibility, category filter purity, reload persistence) evaluate observed behavioral invariants over action-event traces.
- **Relations Evaluated**:
  1. *Sort Reversion Invariance (B05)*: Returning to the initial default sort option must restore the initial catalog ordering. Decoy D06 (equal-price tie-break) is preserved.
  2. *Category Filter Purity (B06)*: When `/api/products` is filtered by a `category` query parameter, all returned items on any page offset (page 1, page 2, etc.) must belong to that category. Decoy D09 (filter reset on reload) is preserved since reset requests omit the query parameter.
  3. *Persistence Across Reload (B07)*: When an acknowledged 2xx mutation writes user profile or address data, a subsequent GET to that endpoint following a reload must return the written data. Decoy D07 (device-only preferences) is preserved.
- **Decoy Safeguards**: Decoys D06, D07, and D09 have dedicated negative control tests and show 0 false positives.
