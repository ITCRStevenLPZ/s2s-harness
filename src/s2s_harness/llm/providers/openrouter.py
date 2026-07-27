"""OpenRouter provider: the OpenAI Python SDK with `base_url` pointed at
OpenRouter's OpenAI-compatible endpoint.

Verified 2026-07-27 against OpenRouter's own "OpenAI SDK" integration guide
(https://openrouter.ai/docs/community/openai-sdk) and the `openai` package's
exception hierarchy
(https://github.com/openai/openai-python/blob/main/src/openai/_exceptions.py)
-- see team_findings.md [T1] for the exact call shape and exception
mapping recorded there. Do not change the call shape without re-verifying
both: OpenRouter's compatibility layer follows OpenAI's SDK conventions,
not the reverse, and the exception hierarchy below is order-sensitive
(`APITimeoutError` is a subclass of `APIConnectionError`; `RateLimitError`
is a subclass of `APIStatusError` -- catch the narrower one first).

Sampling parameters: `max_tokens` (not `max_completion_tokens`) and
`temperature` are both accepted by OpenRouter's parameter reference
(https://openrouter.ai/docs/api-reference/parameters) with standard OpenAI
semantics. No other sampling parameter is sent -- see the module docstring
of `s2s_harness.llm.client` on not widening the `Provider` protocol without
cause.
"""

from __future__ import annotations

import os
from typing import Any

from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

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

_BASE_URL = "https://openrouter.ai/api/v1"
_API_KEY_ENV_VAR = "OPENROUTER_API_KEY"


class OpenRouterProvider:
    name: LLMProviderName = "openrouter"

    def __init__(self, *, api_key: str) -> None:
        # max_retries=0: this provider makes exactly one attempt per call.
        # The SDK's own default retry loop (2 retries) would otherwise
        # multiply worst-case latency to up to 3x timeout_s before
        # LLMClient.complete() ever gets a chance to degrade -- for an
        # interactive CLI, a fast, predictable degrade beats a slow retry
        # that still might fail.
        self._client = OpenAI(base_url=_BASE_URL, api_key=api_key, max_retries=0)

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
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "timeout": timeout_s,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_output_tokens is not None:
            kwargs["max_tokens"] = max_output_tokens
        if response_schema is not None:
            # strict=False deliberately: OpenAI's strict json_schema mode
            # requires every property to appear in "required" (optional
            # fields must be modeled as nullable, not omitted), a
            # constraint T2's mode-scoped schemas do not currently follow
            # (see team_findings.md [T1]). Non-strict mode asks the model
            # to follow the schema without rejecting the request over that
            # constraint; T2's own validation (Pydantic + catalogue
            # membership) is the real conformance check regardless.
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "s2s_role_output",
                    "strict": False,
                    "schema": response_schema,
                },
            }

        try:
            completion = self._client.chat.completions.create(**kwargs)
        except APITimeoutError as exc:
            raise LLMTimeout(str(exc)) from exc
        except APIConnectionError as exc:
            raise LLMConnectionError(str(exc)) from exc
        except RateLimitError as exc:
            raise LLMRateLimited(str(exc)) from exc
        except APIStatusError as exc:
            raise LLMProviderError(str(exc)) from exc
        except APIError as exc:
            raise LLMProviderError(str(exc)) from exc
        except (ConnectionError, OSError) as exc:
            raise LLMConnectionError(str(exc)) from exc

        if not completion.choices:
            raise LLMMalformedResponse("openrouter response had no choices")
        choice = completion.choices[0]
        message = choice.message
        if choice.finish_reason == "content_filter" or getattr(message, "refusal", None):
            raise LLMRefused(f"openrouter refused: finish_reason={choice.finish_reason!r}")
        content = message.content
        if content is None:
            raise LLMMalformedResponse("openrouter response had no message content")
        return ProviderResult(text=content)


def build_openrouter_provider() -> OpenRouterProvider:
    api_key = os.environ.get(_API_KEY_ENV_VAR, "").strip()
    if not api_key:
        raise LLMConfigError(f"S2S_LLM_PROVIDER=openrouter requires {_API_KEY_ENV_VAR} to be set")
    return OpenRouterProvider(api_key=api_key)
