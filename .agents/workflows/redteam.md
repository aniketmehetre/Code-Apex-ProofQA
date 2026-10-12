---
description: Red team audit against milestone guarantees and honesty rules
---

Act as a hostile reviewer, not the author. Try to break the last milestone: tamper one byte in a certificate and run proofqa verify; run with OFFLINE=1; run the import-guard tests; run the pipeline on a clean world and on the decoys and look for false positives; compare every number in docs/claims.md with results/summary.json. Report each failure as a list item with reproduction commands. Do not fix anything in this pass.
