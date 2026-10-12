"""Thin LiteLLM gateway with structured Pydantic validation, disk caching, and offline support."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMGateway:
    """LiteLLM gateway with offline fallback, disk caching, and structured logging."""

    def __init__(
        self,
        cache_dir: Path | str | None = None,
        log_path: Path | str | None = None,
        default_model: str = "gpt-4o-mini",
    ) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir else Path(".cache/llm")
        self.log_path = Path(log_path) if log_path else Path("results/llm_calls.jsonl")
        self.default_model = default_model

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def is_offline(self) -> bool:
        """Returns True if explicitly offline or no LLM provider API keys are configured."""
        if os.getenv("OFFLINE", "0") == "1":
            return True
        keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY"]
        return not any(os.getenv(k) for k in keys)

    def _compute_cache_key(self, prompt: str, schema_name: str, model: str) -> str:
        content = f"{model}:{schema_name}:{prompt}".encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    def complete_structured(
        self,
        prompt: str,
        response_model: type[T],
        system_prompt: str = "You are a web test explorer. Provide valid structured responses.",
        model: str | None = None,
    ) -> T | None:
        """Produces Pydantic-validated structured output with caching and metrics logging.

        Returns None if offline or an unrecoverable model/parsing failure occurs,
        allowing callers to fall back safely to deterministic rule-based algorithms.
        """
        if self.is_offline():
            return None

        chosen_model = model or self.default_model
        cache_key = self._compute_cache_key(prompt, response_model.__name__, chosen_model)
        cache_file = self.cache_dir / f"{cache_key}.json"

        # Check disk cache
        if cache_file.exists():
            try:
                cached_data = json.loads(cache_file.read_text(encoding="utf-8"))
                return response_model.model_validate(cached_data)
            except Exception:
                pass

        # Execute LiteLLM completion
        start_time = time.time()
        try:
            import litellm

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]

            response = litellm.completion(
                model=chosen_model,
                messages=messages,
                response_format=response_model,
                temperature=0.0,
            )

            latency_ms = (time.time() - start_time) * 1000
            content = response.choices[0].message.content
            parsed = response_model.model_validate_json(content)

            usage = getattr(response, "usage", None)
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0
            cost = getattr(response, "_response_cost", 0.0) or 0.0

            # Write to disk cache
            cache_file.write_text(parsed.model_dump_json(indent=2), encoding="utf-8")

            # Write to JSONL log
            self._log_call(
                model=chosen_model,
                prompt_hash=cache_key,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=cost,
                cached=False,
            )

            return parsed
        except Exception as exc:
            # Fallback on any provider exception
            latency_ms = (time.time() - start_time) * 1000
            self._log_call(
                model=chosen_model,
                prompt_hash=cache_key,
                latency_ms=latency_ms,
                prompt_tokens=0,
                completion_tokens=0,
                cost_usd=0.0,
                cached=False,
                error=str(exc),
            )
            return None

    def _log_call(
        self,
        model: str,
        prompt_hash: str,
        latency_ms: float,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        cached: bool,
        error: str | None = None,
    ) -> None:
        entry = {
            "timestamp": time.time(),
            "model": model,
            "prompt_hash": prompt_hash,
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": cost_usd,
            "cached": cached,
            "error": error,
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
