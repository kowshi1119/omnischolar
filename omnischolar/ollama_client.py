# ollama_client.py — Gemma 4 interface
# OmniScholar | wraps the ollama library for chat and embeddings

import concurrent.futures
import os
from typing import Iterator

import ollama

OLLAMA_HOST        = os.getenv("OLLAMA_HOST",        "http://localhost:11434")
OLLAMA_MODEL       = os.getenv("OLLAMA_MODEL",       "gemma4:latest")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_NUM_CTX     = int(os.getenv("OLLAMA_NUM_CTX", "8192"))


class OllamaClient:
    """Thin wrapper around the ollama Python SDK."""

    def __init__(
        self,
        host:        str = OLLAMA_HOST,
        model:       str = OLLAMA_MODEL,
        embed_model: str = OLLAMA_EMBED_MODEL,
        num_ctx:     int = OLLAMA_NUM_CTX,
    ):
        self.host        = host
        self.model       = model
        self.embed_model = embed_model
        self.num_ctx     = num_ctx
        self._client     = ollama.Client(host=host)

    # ── pick best available gemma4 model ─────────────────────────────────────
    def _resolve_model(self) -> str:
        """Return the best available Gemma 4 model name."""
        preferred = ("gemma4:e4b", "gemma4:latest", "gemma4")
        try:
            response = self._client.list()
            available = []
            for item in (response.models if hasattr(response, "models") else response.get("models", [])):
                name = getattr(item, "model", None) or (item.get("model") if isinstance(item, dict) else None)
                if name:
                    available.append(name)
            for candidate in preferred:
                if candidate in available:
                    return candidate
            for name in available:
                if "gemma4" in name:
                    return name
        except Exception:
            pass
        return self.model

    # ── non-streaming chat ────────────────────────────────────────────────────
    def chat(
        self,
        messages:      list,
        system_prompt: str  = "",
        thinking:      bool = False,
        temperature:   float = 0.7,
        num_ctx:       int   = None,
        num_predict:   int   = None,
    ) -> str:
        """
        Send a chat request and return the full response text.
        Prepends system_prompt as a system message when provided.
        """
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        api_messages.extend(messages)

        model = self._resolve_model()
        options = {
            "num_ctx":     num_ctx if num_ctx is not None else self.num_ctx,
            "temperature": temperature,
            "num_predict": num_predict if num_predict is not None else int(os.getenv("OLLAMA_NUM_PREDICT", "512")),
            "num_batch":   int(os.getenv("OLLAMA_NUM_BATCH", "512")),
        }

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    self._client.chat,
                    model=model,
                    messages=api_messages,
                    options=options,
                )
                try:
                    response = future.result(timeout=120)
                except concurrent.futures.TimeoutError:
                    return (
                        "[OmniScholar] Response timed out after 2 minutes. "
                        "Try reducing question count or restarting Ollama."
                    )
            # Handle both dict and object responses
            if hasattr(response, "message"):
                return response.message.content
            return response["message"]["content"]
        except Exception as exc:
            return (
                f"[OmniScholar] Could not reach Ollama model `{model}`. "
                f"Make sure `ollama serve` is running.\n\nError: {exc}"
            )

    # ── streaming chat ────────────────────────────────────────────────────────
    def stream(
        self,
        messages:      list,
        system_prompt: str  = "",
        temperature:   float = 0.7,
        num_ctx:       int   = None,
        num_predict:   int   = None,
    ) -> Iterator[str]:
        """Stream chat tokens. Yields string chunks."""
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        api_messages.extend(messages)

        model = self._resolve_model()
        options = {
            "num_ctx":     num_ctx if num_ctx is not None else self.num_ctx,
            "temperature": temperature,
            "num_predict": num_predict if num_predict is not None else int(os.getenv("OLLAMA_NUM_PREDICT", "512")),
            "num_batch":   int(os.getenv("OLLAMA_NUM_BATCH", "512")),
        }

        try:
            for chunk in self._client.chat(
                model=model,
                messages=api_messages,
                stream=True,
                options=options,
            ):
                content = (
                    chunk.message.content
                    if hasattr(chunk, "message")
                    else chunk.get("message", {}).get("content", "")
                )
                if content:
                    yield content
        except Exception as exc:
            yield (
                f"[OmniScholar] Streaming failed for `{model}`. Error: {exc}"
            )

    # ── embeddings ────────────────────────────────────────────────────────────
    def embed(self, text: str) -> list:
        """Return embedding vector for a string."""
        result = ollama.embeddings(model=self.embed_model, prompt=text)
        return result["embedding"]

    # ── fast chat (speed-optimised for short-output tasks) ────────────────────
    def fast_chat(
        self,
        message: str,
        system: str = "",
        max_tokens: int = 2048,
    ) -> str:
        """
        Optimised for speed: minimal context window, low temperature, capped output.
        Use for quiz evaluation, battle questions, grounding checks, any < 200 word output.
        """
        api_messages = []
        if system:
            api_messages.append({"role": "system", "content": system})
        api_messages.append({"role": "user", "content": message})

        # Always use e2b for fast calls — faster inference
        model = "gemma4:e2b"
        options = {
            "num_ctx": 2048,       # minimal context — faster decode
            "temperature": 0.3,    # lower temp = faster + more deterministic
            "num_predict": max_tokens,
        }

        try:
            response = self._client.chat(
                model=model,
                messages=api_messages,
                options=options,
            )
            if hasattr(response, "message"):
                return response.message.content
            return response["message"]["content"]
        except Exception as exc:
            return (
                f"[OmniScholar] fast_chat failed for `{model}`. Error: {exc}"
            )
