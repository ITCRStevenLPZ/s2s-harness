"""Shared, node-local helpers. Not a public API; every node module below
imports from here directly.

Nothing here calls a model, does I/O, or imports `s2s_harness.llm` /
`s2s_harness.rules` eagerly -- it only knows about `models.state` shapes,
so it stays safe to import from every node regardless of which track that
node belongs to.
"""

from __future__ import annotations

from s2s_harness.models.state import EvaluationState, Suggestion

# `client.py`'s `LLMSkipReason` Literal (`s2s_harness/llm/client.py`) is the
# canonical vocabulary for "why did an LLM role not produce text": T1/T3
# agreed values are "disabled", "timeout", "connection_error",
# "rate_limited", "empty_response", "malformed_response", "refused",
# "provider_error", "cache_hit". Track B nodes reuse those strings
# verbatim via each role's `Outcome.skipped_reason` rather than inventing
# parallel ones. The one case client.py's vocabulary does not cover --
# the role module itself failing to import, or raising something outside
# its own Outcome contract -- is folded into "provider_error" below,
# matching `LLMClient.complete()`'s own catch-all treatment of an
# unclassified exception (client.py:273-281): still a clean degrade, just
# a less specific reason string.
REASON_UNAVAILABLE = "provider_error"

# Reasons specific to nodes in this package that do not map to an LLM
# role's own Outcome at all (the polish node's edge-level gate, per
# team_findings.md [T3] "should_polish vs cache-hit reuse").
REASON_DISABLED = "disabled"
REASON_FINDINGS_HAVE_ERROR = "findings_have_error"
REASON_NO_OVERALL_VERDICT = "no_overall_verdict"

# `EvaluationState` (models/state.py, frozen this wave -- see
# team_findings.md [T3] "BLOCKED item") has no field yet to hold Track
# B's competing verdict. Feature-detect so `nodes/judge.py` and
# `nodes/compare.py` write the richer, typed fields the moment a future
# wave adds them, without every node author re-deriving this check.
HAS_LLM_VERDICT_FIELDS = {"llm_verdict", "llm_reasoning", "llm_confidence"} <= set(
    EvaluationState.model_fields
)
HAS_TRACK_AGREEMENT_FIELD = "track_agreement" in EvaluationState.model_fields


def _suggestion_key(suggestion: Suggestion) -> tuple[str, str, str, str]:
    return (suggestion.side, suggestion.target, suggestion.kind, suggestion.evidence)


def merge_suggestions(
    existing: list[Suggestion], additional: list[Suggestion]
) -> list[Suggestion]:
    """Merge two `Suggestion` lists, deduplicating by `(side, target, kind,
    evidence)`. First occurrence wins; `existing`'s order is preserved and
    `additional` entries are appended in their own order. Used to combine
    `scan`'s (Track A) output with `interpret`'s / `suggest`'s (Track B)
    output without either overwriting the other -- team_plan.md Phase C:
    "merge and dedupe rather than letting one overwrite the other."
    """
    seen = {_suggestion_key(item) for item in existing}
    merged = list(existing)
    for item in additional:
        key = _suggestion_key(item)
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged
