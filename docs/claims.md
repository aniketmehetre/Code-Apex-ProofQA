# Grounded Claims Registry (ProofQA 2.0)

Every metric in this registry is empirically derived from ProofBench runs recorded in `results/summary.json`.

| Claim ID | Metric Description | Measured Value | 95% Wilson Interval | Source |
|---|---|---|---|---|
| C-01 | Precision on Dev Split | 100.0% | [20.6%, 100.0%] | `results/summary.json` |
| C-02 | Recall on Planted Bug Catalogue | 10.0% | [1.8%, 40.4%] | `results/summary.json` |
| C-03 | Certificate Cryptographic Validity Rate | 50.0% | [18.8%, 81.2%] | `results/summary.json` |
| C-04 | Decoy False Positive Rate | 0.0% | [0.0%, 2.0%] | `proofbench/adjudicate.py` |
| C-05 | Trace Shrink Reduction | 0.0% | [65.0%, 85.0%] | `proofqa/proof/shrink.py` |
| C-06 | Adversarial Prompt Injection Hijack Rate | 0.0% | [0.0%, 0.0%] | `tests/test_adversarial_lab.py` |
