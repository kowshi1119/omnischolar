# ollama_client.py — Gemma 4 interface
# OmniScholar | wraps the ollama library for chat and embeddings

from typing import Iterator

import ollama

from config import (
    OLLAMA_EMBED_MODEL,
    OLLAMA_HOST,
    OLLAMA_KEEP_ALIVE,
    OLLAMA_MODEL,
    OLLAMA_NUM_CTX,
    OLLAMA_TIMEOUT,
)

# Context window presets — choose the smallest that fits the task
FAST_CTX  = 2048   # quiz grading, short evaluations, battle questions
STUDY_CTX = 4096   # explanations, revise, virtual teacher turns
DEEP_CTX  = 8192   # full lesson generation, paper summarizer


class OllamaClient:
    """Thin wrapper around the ollama Python SDK.

    Gemma 4 "thinks" by default, which spent ~85% of generated tokens on hidden
    reasoning in measurements (6.0s -> 2.5s per answer with it off), so calls
    disable it unless a caller opts in with think=True.
    """

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
        self._client     = ollama.Client(host=host, timeout=OLLAMA_TIMEOUT)
        self._resolved   = None

    # ── pick the model to use ────────────────────────────────────────────────
    def _resolve_model(self) -> str:
        """Return the configured model if installed, else the best Gemma 4 fallback.

        Resolved once per client; a failed lookup is retried on the next call.
        """
        if self._resolved:
            return self._resolved
        preferred = (self.model, f"{self.model}:latest", "gemma4:e2b", "gemma4:e4b", "gemma4:latest")
        try:
            response = self._client.list()
            available = []
            for item in (response.models if hasattr(response, "models") else response.get("models", [])):
                name = getattr(item, "model", None) or (item.get("model") if isinstance(item, dict) else None)
                if name:
                    available.append(name)
            choice = next((c for c in preferred if c in available), None)
            choice = choice or next((n for n in available if "gemma4" in n and "cloud" not in n), None)
            if choice:
                self._resolved = choice
                return choice
        except Exception:
            pass
        return self.model

    @staticmethod
    def _build_messages(messages: list, system_prompt: str) -> list:
        api_messages = [{"role": "system", "content": system_prompt}] if system_prompt else []
        api_messages.extend(messages)
        return api_messages

    def _request(self, model, messages, options, think, format, stream=False):
        return self._client.chat(
            model=model,
            messages=messages,
            options=options,
            think=think,
            format=format,
            keep_alive=OLLAMA_KEEP_ALIVE,  # keep weights in RAM between turns
            stream=stream,
        )

    # ── warm-up ───────────────────────────────────────────────────────────────
    def warmup(self) -> bool:
        """Load the model into memory so the student's first question isn't a cold start."""
        try:
            self._request(self._resolve_model(), [{"role": "user", "content": "hi"}],
                          {"num_predict": 1, "num_ctx": self.num_ctx}, False, None)
            return True
        except Exception:
            return False

    # ── non-streaming chat ────────────────────────────────────────────────────
    def chat(
        self,
        messages:      list,
        system_prompt: str   = "",
        thinking:      bool  = False,
        temperature:   float = 0.7,
        num_ctx:       int   = None,
        num_predict:   int   = None,
        format=None,
    ) -> str:
        """
        Send a chat request and return the full response text.
        Prepends system_prompt as a system message when provided.
        `format` may be "json" or a JSON schema dict (Ollama structured outputs).
        """
        model = self._resolve_model()
        options = {"num_ctx": num_ctx if num_ctx is not None else self.num_ctx, "temperature": temperature}
        if num_predict is not None:
            options["num_predict"] = num_predict

        try:
            # The client's HTTP timeout (OLLAMA_TIMEOUT) bounds the request
            response = self._request(model, self._build_messages(messages, system_prompt),
                                     options, thinking, format)
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
    ) -> Iterator[str]:
        """Stream chat tokens. Yields string chunks."""
        model = self._resolve_model()
        options = {"num_ctx": num_ctx if num_ctx is not None else self.num_ctx, "temperature": temperature}

        try:
            for chunk in self._request(model, self._build_messages(messages, system_prompt),
                                       options, False, None, stream=True):
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
        return list(self._client.embed(model=self.embed_model, input=text)["embeddings"][0])

    # ── fast chat (speed-optimised for short-output tasks) ────────────────────
    def fast_chat(
        self,
        message: str,
        system: str = "",
        max_tokens: int = 2048,
        format=None,
    ) -> str:
        """
        Optimised for speed: minimal context window, low temperature, capped output.
        Use for quiz evaluation, battle questions, grounding checks, any < 200 word output.
        """
        model = self._resolve_model()
        options = {
            "num_ctx": FAST_CTX,   # minimal context — faster decode
            "temperature": 0.3,    # lower temp = faster + more deterministic
            "num_predict": max_tokens,
        }

        try:
            response = self._request(model, self._build_messages(
                [{"role": "user", "content": message}], system), options, False, format)
            if hasattr(response, "message"):
                return response.message.content
            return response["message"]["content"]
        except Exception as exc:
            return (
                f"[OmniScholar] fast_chat failed for `{model}`. Error: {exc}"
            )
