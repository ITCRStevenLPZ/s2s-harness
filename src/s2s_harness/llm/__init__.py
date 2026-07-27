"""LLM provider layer for the dual-track engine (Wave 3b).

Public surface for the four role modules (`interpret`, `suggest`, `judge`,
`polish`, owned by T2) and for node/CLI wiring (T3/T4). Re-exports from
`s2s_harness.llm.client` so callers do not need to know the submodule split
between the client and `providers/`.

`src/s2s_harness/rules/` and `src/s2s_harness/models/` must never import
from this package -- see CLAUDE.md design rule 1 (amended Wave 3b) and
`scripts/token_boundary_check.py`.
"""

from s2s_harness.llm.client import (
    DEFAULT_MODEL,
    MODEL_ENV_VAR,
    CompletionResult,
    LLMCache,
    LLMClient,
    LLMConfigError,
    LLMConnectionError,
    LlmDegraded,
    LLMEmptyResponse,
    LLMError,
    LLMMalformedResponse,
    LLMOutcome,
    LLMProviderError,
    LLMProviderName,
    LLMRateLimited,
    LLMRefused,
    LLMSkipReason,
    LLMTimeout,
    Provider,
    ProviderResult,
    build_client_from_env,
    complete,
    reset_client_cache,
    resolve_model,
)

__all__ = [
    "DEFAULT_MODEL",
    "MODEL_ENV_VAR",
    "CompletionResult",
    "LLMCache",
    "LLMClient",
    "LLMConfigError",
    "LLMConnectionError",
    "LLMEmptyResponse",
    "LLMError",
    "LLMMalformedResponse",
    "LlmDegraded",
    "LLMOutcome",
    "LLMProviderError",
    "LLMProviderName",
    "LLMRateLimited",
    "LLMRefused",
    "LLMSkipReason",
    "LLMTimeout",
    "Provider",
    "ProviderResult",
    "build_client_from_env",
    "complete",
    "reset_client_cache",
    "resolve_model",
]
