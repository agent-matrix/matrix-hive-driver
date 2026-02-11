"""Optional LLM provider for local development and CI verification.

The main LLM lives in Matrix AI — Architect calls it, not us.
This module is a lightweight fallback so developers can run local
verification steps (e.g. plan-IR sanity checks, node summaries)
without requiring Matrix AI to be running.

Usage:
    LLM_PROVIDER=none      →  NoOpProvider (default, returns empty)
    LLM_PROVIDER=ollama     →  OllamaProvider (local Ollama with llama3.1:8b)

In CI, the provider gracefully degrades: if Ollama is unreachable the
provider returns a structured error instead of crashing the pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

from matrix_hive_driver.driver.config import settings

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    provider: str
    ok: bool
    error: str | None = None


class LLMProvider(Protocol):
    def complete(self, prompt: str, **kwargs: Any) -> LLMResponse: ...

    def is_available(self) -> bool: ...


# ---------------------------------------------------------------------------
# NoOp — default when no local LLM is configured
# ---------------------------------------------------------------------------
class NoOpProvider:
    """Returns empty responses. Used when LLM_PROVIDER=none."""

    def complete(self, prompt: str, **kwargs: Any) -> LLMResponse:
        return LLMResponse(
            text="",
            model="none",
            provider="noop",
            ok=True,
        )

    def is_available(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# Ollama — optional local LLM for dev/CI verification
# ---------------------------------------------------------------------------
class OllamaProvider:
    """Talks to a local Ollama instance. Gracefully degrades if unavailable."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1:8b",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def complete(self, prompt: str, **kwargs: Any) -> LLMResponse:
        try:
            import httpx
        except ImportError:
            return LLMResponse(
                text="",
                model=self.model,
                provider="ollama",
                ok=False,
                error="httpx not installed — install with: uv sync --extra ollama",
            )

        try:
            resp = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    **kwargs,
                },
                timeout=120.0,
            )
            if resp.status_code >= 400:
                return LLMResponse(
                    text="",
                    model=self.model,
                    provider="ollama",
                    ok=False,
                    error=f"Ollama returned {resp.status_code}: {resp.text[:300]}",
                )
            data = resp.json()
            return LLMResponse(
                text=str(data.get("response", "")),
                model=self.model,
                provider="ollama",
                ok=True,
            )
        except Exception as exc:
            return LLMResponse(
                text="",
                model=self.model,
                provider="ollama",
                ok=False,
                error=f"Ollama unreachable: {exc}",
            )

    def is_available(self) -> bool:
        try:
            import httpx

            resp = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def get_llm_provider() -> LLMProvider:
    """Return the configured LLM provider based on settings.llm_provider."""
    provider_name = settings.llm_provider.lower().strip()

    if provider_name == "ollama":
        log.info("LLM provider: Ollama (%s @ %s)", settings.ollama_model, settings.ollama_base_url)
        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )

    # Default: no LLM
    if provider_name != "none":
        log.warning("Unknown LLM_PROVIDER=%r, falling back to noop", provider_name)
    return NoOpProvider()
