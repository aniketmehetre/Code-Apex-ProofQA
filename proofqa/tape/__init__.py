"""Append-only JSONL tape recording, loading, and noise floor profiling."""

from __future__ import annotations

from proofqa.tape.noise import NoiseProfile, noise_floor
from proofqa.tape.recorder import TapeRecorder
from proofqa.tape.tape import Tape, signature_from_events

__all__ = [
    "NoiseProfile",
    "Tape",
    "TapeRecorder",
    "noise_floor",
    "signature_from_events",
]
