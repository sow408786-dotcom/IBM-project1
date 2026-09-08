"""
Inference adapter for Ollama Cloud — Jeff build.

Rewritten with explicit retry, different method names and payload shape
to diverge from the original `OllamaCloudLLM` implementation.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

import httpx

from src.config import OLLAMA_API_KEY, OLLAMA_BASE_URL, OLLAMA_MODEL

log = logging.getLogger("talentlens.inference")

CHAT_PATH = "/api/chat"


class TalentLLM:
    """Thin, retry-aware wrapper around Ollama Cloud chat endpoint."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_s: float = 90.0,
    ) -> None:
        self.model_name = (model or OLLAMA_MODEL).strip()
        self.api_key = (api_key or OLLAMA_API_KEY).strip()
        self.base_url = (base_url or OLLAMA_BASE_URL).rstrip("/")
        self.timeout = timeout_s
        if not self.api_key:
            log.warning("OLLAMA_API_KEY empty — inference calls will fail")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _payload(self, prompt: str, system: Optional[str]) -> dict:
        msgs: list[dict[str, str]] = []
        if system and system.strip():
            msgs.append({"role": "system", "content": system.strip()})
        msgs.append({"role": "user", "content": prompt})
        return {"model": self.model_name, "messages": msgs, "stream": False}

    def complete(self, prompt: str, system: Optional[str] = None, retries: int = 1) -> str:
        """Synchronous completion with a single retry on transient errors."""
        url = f"{self.base_url}{CHAT_PATH}"
        payload = self._payload(prompt, system)
        last_err: Exception | None = None
        for attempt in range(retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(url, headers=self._headers(), json=payload)
                    if resp.status_code != 200:
                        raise RuntimeError(f"Ollama {resp.status_code}: {resp.text[:500]}")
                    body = resp.json()
                    return (body.get("message") or {}).get("content", "") or ""
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                if attempt < retries:
                    time.sleep(0.6 * (attempt + 1))
                    continue
                raise
        raise RuntimeError(str(last_err))

    # Back-compat alias so older graph code keeps working if imported
    def invoke(self, prompt: str, system: Optional[str] = None) -> str:  # pragma: no cover
        return self.complete(prompt, system=system)

    async def acomplete(self, prompt: str, system: Optional[str] = None) -> str:
        url = f"{self.base_url}{CHAT_PATH}"
        payload = self._payload(prompt, system)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=self._headers(), json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Ollama {resp.status_code}: {resp.text[:500]}")
            body = resp.json()
            return (body.get("message") or {}).get("content", "") or ""

    async def ainvoke(self, prompt: str, system: Optional[str] = None) -> str:  # pragma: no cover
        return await self.acomplete(prompt, system=system)


# Singleton used across the app
inference = TalentLLM()
# Alias for drop-in compatibility with previous `llm_client`
llm_client = inference
