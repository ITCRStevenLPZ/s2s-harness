"""LLM provider client: protocol, factory, content-addressed cache, and
degradation policy for the dual-track engine {GRAPH-8}.

This module and `s2s_harness.llm.providers` are the sanctioned places an LLM
SDK is imported for Track B, per CLAUDE.md design rule 1 (amended Wave 3b):
`src/s2s_harness/rules/` and `src/s2s_harness/models/` stay model-free, and
that is the boundary `scripts/token_boundary_check.py` and
`tests/test_token_boundary.py` enforce. Nothing here is imported by either
of those two packages.

Two failure regimes, deliberately different:

- **Configuration errors** (unknown `S2S_LLM_PROVIDER`, missing API key for
  the selected provider) raise `LLMConfigError` at construction time --
  loud, at startup, never a request-time surprise. Precedent:
  `docs/STT_SPEC.md` {STT-12}, "no credentials configured" is a startup
  error for the STT layer; provider selection here follows the same
  discipline.
- **Runtime provider failures** (timeout, connection error, rate limit,
  empty response, malformed response, provider refusal) never raise out of
  `LLMClient.complete()`. They come back as a degraded `LLMOutcome` so the
  caller falls back to its Track A equivalent. The tool never blocks on a
  provider.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

logger = logging.getLogger(__name__)

LLMProviderName = Literal["openrouter", "gemini"]

# Canonical vocabulary for `EvaluationState.llm_skipped_reason` {GRAPH-8} and
# any equivalent per-role "why did Track B not run" field `interpret` /
# `suggest` / `judge` end up needing. T2/T3/T4: use these exact strings, do
# not invent parallel ones per role.
#
# Six of these are genuine runtime-degradation causes -- every one of them
# is an exception inside a provider that gets demoted to a value here and
# never propagates further. "disabled" and "cache_hit" are not failures and
# are never raised by this module; a caller sets "disabled" itself when
# Track B is off (`--no-llm` / `S2S_NO_LLM=1` / no provider configured),
# and `LLMOutcome.skipped_reason` is set to "cache_hit" by `LLMClient`
# itself when a cached completion satisfies the request without a network
# call -- `LLMOutcome.ok` is still `True` in that case, there is text to
# use, "cache_hit" is metadata about how it was obtained, not a failure.
LLMSkipReason = Literal[
    "disabled",
    "timeout",
    "connection_error",
    "rate_limited",
    "empty_response",
    "malformed_response",
    "refused",
    "provider_error",
    "cache_hit",
]


class LLMConfigError(Exception):
    """A configuration problem: unknown `S2S_LLM_PROVIDER` value, or a
    missing API key for the selected provider. Raised only from
    `build_client_from_env()` / `build_*_provider()`, at construction time.
    Never raised from `LLMClient.complete()` -- that path only degrades.
    """


class LLMError(Exception):
    """Base for every runtime provider failure a `Provider.complete()`
    implementation raises. `LLMClient.complete()` catches this hierarchy
    (and any other exception, as an unclassified `provider_error`
    fallback) and converts it to a degraded `LLMOutcome`. Never expected to
    reach a role or node.
    """

    reason: LLMSkipReason = "provider_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)


class LLMTimeout(LLMError):
    reason: LLMSkipReason = "timeout"


class LLMConnectionError(LLMError):
    reason: LLMSkipReason = "connection_error"


class LLMRateLimited(LLMError):
    reason: LLMSkipReason = "rate_limited"


class LLMEmptyResponse(LLMError):
    reason: LLMSkipReason = "empty_response"


class LLMMalformedResponse(LLMError):
    reason: LLMSkipReason = "malformed_response"


class LLMRefused(LLMError):
    reason: LLMSkipReason = "refused"


class LLMProviderError(LLMError):
    """Catch-all for a provider failure that does not fit one of the more
    specific categories above -- an unrecognized SDK exception, an
    unexpected 5xx, or the like. Still a clean degrade, just a less
    specific reason string.
    """

    reason: LLMSkipReason = "provider_error"


@dataclass(frozen=True)
class ProviderResult:
    """What a `Provider.complete()` implementation returns on success. Text
    is returned as-is, not stripped or validated -- `LLMClient.complete()`
    owns the empty-response check centrally so every provider applies the
    same rule instead of each reimplementing it slightly differently.
    """

    text: str


class Provider(Protocol):
    """Minimal surface every LLM role needs: a system prompt plus user
    content in, text back. Deliberately not a general-purpose SDK wrapper
    -- no streaming, no tool calls, no multi-turn history. If a role needs
    more than this, that is a spec gap to raise, not a reason to widen this
    protocol quietly.

    Implementations raise an `LLMError` subclass on any failure. They never
    return an empty string to signal failure -- raise instead. They never
    raise for an empty-but-successful completion either; that is
    `LLMClient.complete()`'s call to make, uniformly, not the provider's.
    """

    name: LLMProviderName

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
    ) -> ProviderResult: ...


@dataclass(frozen=True)
class LLMOutcome:
    """Result of `LLMClient.complete()`. `ok=False` means: use your Track A
    equivalent, and if you have an `llm_skipped_reason`-shaped field,
    record `skipped_reason` in it verbatim.
    """

    ok: bool
    text: str
    skipped_reason: LLMSkipReason | Literal[""] = ""
    cached: bool = False


class LLMCache:
    """Content-addressed cache for LLM completions, under `.s2s-cache/llm/`
    (gitignored). Key: `sha256(input_text + role + prompt_version)`.

    The point: re-running an evaluation after fixing an unrelated field
    produces the same input for a given role and therefore costs nothing
    the second time. `prompt_version` is supplied by the caller (each
    role's own `PROMPT_VERSION`, T2) rather than imported here -- this
    module must not depend on the role modules, or the dependency points
    the wrong way.

    Deliberately simple: one file per entry, plain text, no expiry, no
    metadata beyond the file itself. This is a cost-avoidance cache, not a
    durable store, and is safe to delete at any time.
    """

    def __init__(self, root: Path | None = None) -> None:
        self._root = root if root is not None else Path(".s2s-cache") / "llm"

    def _path(self, *, role: str, prompt_version: str, input_text: str) -> Path:
        # \x1f (unit separator) between fields so ("ab", "c") and ("a",
        # "bc") never collide just because plain concatenation would make
        # them look identical.
        digest = hashlib.sha256(
            (input_text + "\x1f" + role + "\x1f" + prompt_version).encode("utf-8")
        ).hexdigest()
        return self._root / role / f"{digest}.txt"

    def get(self, *, role: str, prompt_version: str, input_text: str) -> str | None:
        path = self._path(role=role, prompt_version=prompt_version, input_text=input_text)
        if not path.exists():
            return None
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            logger.warning("llm cache read failed for %s, treating as a miss", path)
            return None

    def set(self, *, role: str, prompt_version: str, input_text: str, output_text: str) -> None:
        path = self._path(role=role, prompt_version=prompt_version, input_text=input_text)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(output_text, encoding="utf-8")
        except OSError:
            logger.warning("llm cache write failed for %s, continuing without caching", path)


class LLMClient:
    """Wraps one `Provider` with the cache and the degradation policy every
    role shares. Roles call `complete()`; they never touch a `Provider` or
    an SDK exception directly.
    """

    def __init__(self, provider: Provider, *, cache: LLMCache | None = None) -> None:
        self.provider = provider
        self._cache = cache

    @property
    def provider_name(self) -> LLMProviderName:
        return self.provider.name

    def complete(
        self,
        *,
        role: str,
        prompt_version: str,
        model: str,
        system_prompt: str,
        user_content: str,
        response_schema: dict[str, Any] | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        timeout_s: float = 30.0,
    ) -> LLMOutcome:
        cache_input = system_prompt + "\x1e" + user_content

        if self._cache is not None:
            cached_text = self._cache.get(
                role=role, prompt_version=prompt_version, input_text=cache_input
            )
            if cached_text is not None:
                return LLMOutcome(
                    ok=True, text=cached_text, skipped_reason="cache_hit", cached=True
                )

        try:
            result = self.provider.complete(
                model=model,
                system_prompt=system_prompt,
                user_content=user_content,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                timeout_s=timeout_s,
                response_schema=response_schema,
            )
        except LLMError as exc:
            logger.warning(
                "llm degraded role=%s provider=%s reason=%s: %s",
                role,
                self.provider.name,
                exc.reason,
                exc,
            )
            return LLMOutcome(ok=False, text="", skipped_reason=exc.reason)
        except Exception as exc:  # noqa: BLE001 - last-resort backstop, see module docstring
            logger.warning(
                "llm degraded role=%s provider=%s reason=provider_error (unclassified %s): %s",
                role,
                self.provider.name,
                type(exc).__name__,
                exc,
            )
            return LLMOutcome(ok=False, text="", skipped_reason="provider_error")

        text = result.text.strip()
        if not text:
            logger.warning(
                "llm degraded role=%s provider=%s reason=empty_response", role, self.provider.name
            )
            return LLMOutcome(ok=False, text="", skipped_reason="empty_response")

        if self._cache is not None:
            self._cache.set(
                role=role, prompt_version=prompt_version, input_text=cache_input, output_text=text
            )
        return LLMOutcome(ok=True, text=text)


_PROVIDER_ENV_VAR = "S2S_LLM_PROVIDER"
_KNOWN_PROVIDERS: tuple[LLMProviderName, ...] = ("openrouter", "gemini")


def build_client_from_env(*, cache: LLMCache | None = None) -> LLMClient | None:
    """Construct an `LLMClient` from environment configuration. No network
    call happens here -- only environment reads and SDK client construction.

    Returns `None` when `S2S_LLM_PROVIDER` is unset or empty. That is a
    legitimate steady state (a Track-A-only run, e.g. `--no-llm` used by
    default, or an operator who never set up an LLM provider at all), not a
    configuration error -- callers treat `None` the same way they treat a
    degraded `LLMOutcome`, recording `llm_skipped_reason = "disabled"`.

    Raises `LLMConfigError` immediately for:
    - an `S2S_LLM_PROVIDER` value that is set but not one of
      `_KNOWN_PROVIDERS` (never a silent fallback to a default provider);
    - a known provider missing its required API key.

    Judgment call, not spelled out in GRAPH_SPEC/CLI_SPEC: whether "unset"
    should instead be its own hard error. Recorded in team_findings.md
    [T1] for T5 to confirm or override when `.env.example` /
    `docs/CLI_SPEC.md` are amended for the dual-track providers.
    """
    raw = os.environ.get(_PROVIDER_ENV_VAR, "").strip()
    if not raw:
        return None
    if raw not in _KNOWN_PROVIDERS:
        raise LLMConfigError(
            f"{_PROVIDER_ENV_VAR}={raw!r} is not a known provider; expected one of "
            f"{_KNOWN_PROVIDERS}"
        )
    provider = _build_provider(raw)
    return LLMClient(provider, cache=cache if cache is not None else LLMCache())


def _build_provider(name: LLMProviderName) -> Provider:
    if name == "openrouter":
        from s2s_harness.llm.providers.openrouter import build_openrouter_provider

        return build_openrouter_provider()
    if name == "gemini":
        from s2s_harness.llm.providers.gemini import build_gemini_provider

        return build_gemini_provider()
    raise LLMConfigError(f"unreachable: unhandled provider {name!r}")  # pragma: no cover


_MODEL_ENV_VAR = "S2S_LLM_MODEL"

# Judgment call, flagged for T5: no per-role model selection this wave, one
# model per provider for all four roles. `S2S_LLM_MODEL` overrides either
# default. Model names drift fast; treat these two as placeholders to
# revisit, not a considered recommendation.
_DEFAULT_MODEL: dict[LLMProviderName, str] = {
    "openrouter": "openai/gpt-4o-mini",
    "gemini": "gemini-2.5-flash",
}


def _resolve_model(provider_name: LLMProviderName, override: str | None) -> str:
    if override:
        return override
    env_override = os.environ.get(_MODEL_ENV_VAR, "").strip()
    if env_override:
        return env_override
    return _DEFAULT_MODEL[provider_name]


class LlmDegraded(Exception):
    """Raised by the async `complete()` facade below -- the surface every
    LLM role (T2: `interpret`/`suggest`/`judge`/`polish`) actually calls.
    Every runtime degradation case funnels through this one exception
    type; `reason` is one of `LLMSkipReason` and is what a role copies
    into `llm_skipped_reason` or an equivalent per-role field. Roles
    should inspect `.reason` rather than catching this bare -- catching it
    bare and mapping every case to the same generic reason string throws
    away exactly the distinction (timeout vs. rate-limited vs. malformed)
    an auditor or a retry policy would want later.
    """

    def __init__(self, reason: LLMSkipReason, message: str = "") -> None:
        super().__init__(message or reason)
        self.reason = reason


@dataclass(frozen=True)
class CompletionResult:
    """Successful return of the async `complete()` facade.

    `data` is reserved for a provider that hands back an already-parsed
    structured payload; no provider implementation does that today (see
    `Provider.complete()`'s `response_schema` note), so `data` is always
    `None` currently. Callers that pass `schema` parse `text` as JSON
    themselves -- do not rely on `data` until a provider actually
    populates it.
    """

    text: str
    data: dict[str, Any] | None = None
    cached: bool = False


_client: LLMClient | None = None
_client_resolved = False


def _get_client() -> LLMClient | None:
    """Lazily build and cache the process-wide `LLMClient` from environment
    configuration. Deliberately a plain module-level cache, not a
    dependency-injected singleton -- this module has exactly one
    configured provider per process, selected once at first use, matching
    `S2S_LLM_PROVIDER` being a startup-time, not a per-call, choice.
    """
    global _client, _client_resolved
    if not _client_resolved:
        _client = build_client_from_env()
        _client_resolved = True
    return _client


def reset_client_cache(client: LLMClient | None = None, *, resolved: bool = False) -> None:
    """Test-only escape hatch. Reassigns the module-level client cache
    `_get_client()` reads, so a test can either inject a stub `LLMClient`
    (`client=stub, resolved=True`) or force the next `complete()` call to
    re-read the environment (`resolved=False`, the default -- e.g. after
    changing `S2S_LLM_PROVIDER` mid-test). Production code never calls
    this; the module resolves its client exactly once per process.
    """
    global _client, _client_resolved
    _client = client
    _client_resolved = resolved


async def complete(
    *,
    role: str,
    system: str,
    user: str,
    prompt_version: str,
    schema: dict[str, Any] | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
    timeout_s: float = 30.0,
) -> CompletionResult:
    """Async facade every LLM role calls -- the actual integration point
    for `interpret`/`suggest`/`judge`/`polish` (T2).

    Raises `LlmDegraded` on every failure case: no provider configured,
    any runtime provider failure, or an empty response. There is no
    sentinel return value for failure, so a role cannot forget to handle
    it -- always wrap the call in `try/except LlmDegraded`.

    `schema` is a best-effort structured-output hint, forwarded to
    whichever provider is configured (see each provider module for the
    exact wire shape and its caveats -- OpenRouter/OpenAI's JSON-schema
    dialect and Gemini's are not the same dialect, and this facade does
    not translate between them). It does not change what is returned:
    `text` is always the provider's raw text; parse it as JSON yourself
    when you passed a schema. If a provider rejects a schema it cannot
    honor, that surfaces as a normal degrade (`LlmDegraded`), not a crash
    -- the same safety net covers a schema that does not fit a given
    provider's dialect as covers any other provider failure.

    Synchronous under the hood: both providers today are synchronous SDK
    clients (see their modules for why), so this awaits
    `asyncio.to_thread(...)` rather than a native async HTTP call. That is
    an implementation detail -- from a role's perspective this is a normal
    coroutine that does not block the event loop.
    """
    client = _get_client()
    if client is None:
        raise LlmDegraded("disabled", "no LLM provider configured (S2S_LLM_PROVIDER unset)")

    resolved_model = _resolve_model(client.provider_name, model)
    outcome = await asyncio.to_thread(
        client.complete,
        role=role,
        prompt_version=prompt_version,
        model=resolved_model,
        system_prompt=system,
        user_content=user,
        response_schema=schema,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        timeout_s=timeout_s,
    )
    if not outcome.ok:
        raise LlmDegraded(outcome.skipped_reason or "provider_error")
    return CompletionResult(text=outcome.text, data=None, cached=outcome.cached)
