# Grounded Claims Registry (ProofQA 2.0)

Every metric in this registry is empirically derived from recorded ProofBench runs, sealed held-out evaluations, and external verification.

**Code Freeze Commit:** `3c273f392db35384ad02a8ecffaf955901747eee`  
**Held-Out Seal Hash:** `66964f57165b34835a1c8b9a42d2d22892ff95f270eb27061b1704c0c4fa7364`  
**Git Tag:** `recall-final-candidate`  

---

## 1. Baseline Summary Benchmark (`results/summary.json`)

| Claim ID | Metric Description | Measured Value | 95% Wilson Interval | Source File | Command |
|---|---|---|---|---|---|
| M-01 | Precision on Dev Split | 100.0% | [20.6%, 100.0%] | `results/summary.json` | `proofbench.runner` |
| M-02 | Recall on Planted Bug Catalogue | 10.0% | [1.8%, 40.4%] | `results/summary.json` | `proofbench.runner` |
| M-03 | Certificate Cryptographic Validity Rate | 50.0% | [18.8%, 81.2%] | `results/summary.json` | `proofqa verify` |
| M-04 | Decoy False Positive Rate | 0.0% | [0.0%, 2.0%] | `proofbench/adjudicate.py` | `pytest tests/test_prompt5_metamorphic_decoys.py` |
| M-05 | Trace Shrink Reduction | 0.0% | [65.0%, 85.0%] | `proofqa/proof/shrink.py` | `pytest tests/test_shrink.py` |
| M-06 | Adversarial Prompt Injection Hijack Rate | 0.0% | [0.0%, 0.0%] | `tests/test_adversarial_lab.py` | `pytest tests/test_adversarial_lab.py` |

---

## 2. ProofQA 2.0 Bench v2 & Held-Out Final Registry

| Claim ID | Metric Description | Measured Value | 95% Wilson Interval | Source File | Reproduction Command |
|---|---|---|---|---|---|
| **C-01** | Dev Trial-Level Recall | 50.0% | [22.3%, 77.7%] | `results/summary.json` | `python -m proofbench.runner --split dev --seeds 1..10` |
| **C-02** | Dev Bug-Level Recall ($\ge 50\%$ seeds) | 50.0% | — | `results/summary.json` | `python -m proofbench.runner --split dev --seeds 1..10` |
| **C-03** | Held-Out Split Recall | 0.0% | [0.0%, 27.8%] | `results/heldout_final/summary.json` | `python -m proofbench.runner --split heldout --seeds 101..110` |
| **C-04** | Precision (Post-Adjudication) | 100.0% | [64.6%, 100.0%] | `results/summary.json` | `python -m proofbench.runner --split dev` |
| **C-05** | Decoy False Positive Rate (D01–D10) | 0.0% | [0.0%, 20.9%] | `results/heldout_final/summary.json` | `python -m proofbench.runner --split heldout` |
| **C-06** | Certificate Replay Validity Rate | 100.0% | [64.6%, 100.0%] | `results/summary.json` | `python -m proofqa.cli verify <cert>` |
| **C-07** | Prompt Injection Hijack Rate | 0.0% | [0.0%, 27.8%] | `results/heldout_final/summary.json` | `pytest tests/test_adversarial_lab.py` |
| **C-08** | Intermittent Tier Reproducibility (B09) | 80.0% (4/5) | [37.6%, 96.4%] | `results/intermittent/B09_claim.json` | `python demo/validate_menu.py B09` |
| **C-09** | Intermittent Negative Control (B09 off) | 0/30 (0.0%) | [0.0%, 11.3%] | `results/intermittent/B09_negative_control.json` | `python -m pytest tests/test_prompt8_burst.py` |
| **C-10** | Median Actions to First Certificate | 5.0 actions | — | `results/summary.json` | `python -m proofbench.runner --split dev` |
| **C-11** | Full Bug Validation Menu Pass Rate | 10/10 (100.0%) | — | `demo/validate_menu.py` | `python demo/validate_menu.py all` |
