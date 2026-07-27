"""`suggest`. Track B role, new this wave -- no `GRAPH-n` id yet (posted
to T5 in `team_findings.md` [T3] for `docs/GRAPH_SPEC.md`; proposed
`{GRAPH-17}`).

Reads: state (notes plus the catalogue). Writes: `suggestions` (merged
with whatever is already there).

Wraps `s2s_harness.llm.suggest.suggest(state) -> SuggestOutcome`.
`SuggestOutcome.value` is already `list[Suggestion] | None` -- the exact
same shape `scan` emits (team_plan.md Phase B: "`Suggestion[]`, same
shape `scan` emits, merged and deduped with regex results") -- so this
node does no shape conversion at all, only merging.

Degrades to a no-op update (`{}`) when `s2s_harness.llm.suggest` is
unavailable, disabled, or its own call fails.
"""

from __future__ import annotations

from typing import Any

from s2s_harness.models.state import EvaluationState
from s2s_harness.nodes._common import merge_suggestions


async def suggest(state: EvaluationState) -> dict[str, Any]:
    try:
        from s2s_harness.llm.suggest import suggest as _llm_suggest
    except ImportError:
        return {}

    try:
        outcome = await _llm_suggest(state)
    except Exception:  # noqa: BLE001 - degrade, never block the graph
        return {}

    if outcome.value is None or not outcome.value:
        return {}

    return {"suggestions": merge_suggestions(state.suggestions, outcome.value)}
