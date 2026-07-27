"""Gemini provider: `google-genai` against Gemini AI Studio (not Vertex).

Verified 2026-07-27 against the official python-genai docs and source
(https://googleapis.github.io/python-genai/, https://github.com/googleapis/
python-genai) -- see team_findings.md [T1] for the exact call shape,
`GenerateContentConfig` fields, and `google.genai.errors` class hierarchy
(`APIError` base, `ClientError` for 4xx, `ServerError` for 5xx) recorded
there.

Timeout is handled outside the SDK on purpose. `google-genai`'s own
client/http_options-level timeout has open, unresolved reports of being
ineffective (googleapis/python-genai#911; pydantic-ai#4031) -- exactly the
failure mode this provider exists to prevent. `complete()` instead runs the
call in a worker thread and enforces the wall-clock budget itself via
`Future.result(timeout=...)`, treating an unfinished call as `LLMTimeout`
regardless of what the SDK's internal timeout does.

Known residual limitation, not solved here: `Future.cancel()` cannot stop a
call already in flight, only a call not yet started. If the underlying
socket call itself never returns (a true hang, not merely a slow response),
the background thread outlives the timeout we report to the caller, and
`concurrent.futures`' interpreter-shutdown hook will still try to join it,
which can delay process exit. A new `ThreadPoolExecutor` is created per
call (not held on the instance) so a stuck call cannot block *subsequent*
calls from getting a fresh worker -- that is the failure mode this design
does close. Fully hard-killing a hung call would need a subprocess, not a
thread; out of scope for this wave, flagged rather than silently accepted.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Any

from google import genai
from google.genai import types
from google.genai.errors import APIError, ClientError, ServerError

from s2s_harness.llm.client import (
    LLMConfigError,
    LLMConnectionError,
    LLMMalformedResponse,
    LLMProviderError,
    LLMProviderName,
    LLMRateLimited,
    LLMRefused,
    LLMTimeout,
    ProviderResult,
)

_API_KEY_ENV_VAR = "GEMINI_API_KEY"

# finish_reason values that mean the model declined or was blocked, as
# distinct from a normal "STOP" / "MAX_TOKENS" completion. Names per the
# Gemini API's FinishReason enum.
_BLOCKED_FINISH_REASONS = frozenset(
    {"SAFETY", "RECITATION", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "OTHER"}
)


class GeminiProvider:
    name: LLMProviderName = "gemini"

    def __init__(self, *, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key)

    def complete(
        self,
        *,
        model: str,
        system_prompt: str,
        user_content: str,
        temperature: float | None,
        max_output_tokens: int | None,
        timeout_s: float,
        response_schema: dict[str, Any] | None = None,
    ) -> ProviderResult:
        config_kwargs: dict[str, Any] = {"system_instruction": system_prompt}
        if temperature is not None:
            config_kwargs["temperature"] = temperature
        if max_output_tokens is not None:
            config_kwargs["max_output_tokens"] = max_output_tokens
        if response_schema is not None:
            # Best-effort only: Gemini's schema dialect (uppercase type
            # names, `nullable` instead of a type/null union, no confirmed
            # `additionalProperties` support) is NOT the same dialect as
            # the standard JSON Schema T2's role modules build (see
            # team_findings.md [T1]). Passing a standard-JSON-Schema dict
            # here is unverified -- if Gemini rejects it, that surfaces as
            # a normal `LLMProviderError` degrade below, not a crash, so
            # an imperfect schema is safe, just not guaranteed to work.
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = response_schema
        config = types.GenerateContentConfig(**config_kwargs)

        def _call() -> object:
            return self._client.models.generate_content(
                model=model,
                contents=user_content,
                config=config,
            )

        # Per-call executor, not held on the instance: see module docstring.
        # shutdown(wait=False) here does not block this call on a stuck
        # thread; it just stops waiting for it.
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gemini-llm")
        try:
            future = executor.submit(_call)
            try:
                response = future.result(timeout=timeout_s)
            except FutureTimeoutError as exc:
                raise LLMTimeout(f"gemini call exceeded {timeout_s}s") from exc
            except ClientError as exc:
                if getattr(exc, "code", None) == 429:
                    raise LLMRateLimited(str(exc)) from exc
                raise LLMProviderError(str(exc)) from exc
            except ServerError as exc:
                raise LLMProviderError(str(exc)) from exc
            except APIError as exc:
                raise LLMProviderError(str(exc)) from exc
            except (ConnectionError, OSError) as exc:
                raise LLMConnectionError(str(exc)) from exc
        finally:
            executor.shutdown(wait=False)

        feedback = getattr(response, "prompt_feedback", None)
        if feedback is not None and getattr(feedback, "block_reason", None):
            raise LLMRefused(f"gemini blocked the prompt: {feedback.block_reason!r}")

        candidates = getattr(response, "candidates", None) or []
        if candidates:
            finish_reason = getattr(candidates[0], "finish_reason", None)
            finish_reason_name = getattr(finish_reason, "name", finish_reason)
            if finish_reason_name in _BLOCKED_FINISH_REASONS:
                raise LLMRefused(f"gemini finish_reason={finish_reason_name!r}")

        try:
            text = response.text  # type: ignore[attr-defined]
        except ValueError as exc:
            raise LLMMalformedResponse(f"gemini response had no text: {exc}") from exc
        if text is None:
            raise LLMMalformedResponse("gemini response text was None")
        return ProviderResult(text=text)


def build_gemini_provider() -> GeminiProvider:
    api_key = os.environ.get(_API_KEY_ENV_VAR, "").strip()
    if not api_key:
        raise LLMConfigError(f"S2S_LLM_PROVIDER=gemini requires {_API_KEY_ENV_VAR} to be set")
    return GeminiProvider(api_key=api_key)
