# RECORDED RUN FALLBACK (ProofQA 2.0)

> [!IMPORTANT]
> **RECORDED FALLBACK RUN**
> This directory contains pre-recorded, cryptographically sealed bug certificates for offline demonstration fallback.
> In accordance with AGENTS.md Rule 60 ("Never present recorded output as live. Label recorded runs."), all data herein is explicitly designated as **RECORDED**.

## Recorded Certified Finding: B01 (ZeroQuantityException)
- **Status**: RECORDED
- **Verifier Verdict**: VALID (SHA-256 Verified)
- **App Target**: Shop Twin (v1.0.0)
- **Failure Endpoint**: `POST /api/cart` -> 500 Internal Server Error
- **Minimal Reproduction Trace**:
  1. `GOTO /`
  2. `CLICK "Noise-Canceling Wireless Headphones"`
  3. `FILL Quantity "0"`
  4. `CLICK "Confirm Add to Cart"`
