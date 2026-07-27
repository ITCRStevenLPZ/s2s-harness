"""`interpret`. Track B role, new this wave -- no `GRAPH-n` id yet (posted
to T5 in `team_findings.md` [T3] for `docs/GRAPH_SPEC.md`; proposed
`{GRAPH-16}`).

Reads: state (free-form rater notes on both sides). Writes:
`suggestions` (merged with whatever is already there, never replacing
it).

Wraps `s2s_harness.llm.interpret.interpret(state) -> InterpretOutcome`.
That role proposes structured best/worst/candidate flags per side
(`InterpretResult.a` / `.b`, each an `InterpretedSide`) -- "proposed, not
written" (team_plan.md). Converting that proposal into `Suggestion`
entries (`kind="tone"`, `target="best"` / `"worst"` / a candidate
catalogue key, `evidence` = the proposed text) keeps `interpret` on the
exact same reportable, never-auto-applied shape `scan` and `suggest`
already use, so no new model is needed (`team_findings.md` [T3]
"Suggestion/Finding encoding conventions for Track B") -- accepting a
proposal into a real flag is still an explicit caller action, matching
`scan`'s own suggestion behavior.

Degrades to a no-op update (`{}`) when `s2s_harness.llm.interpret` is
unavailable, disabled, or its own call fails -- Track A's `suggestions`
from `scan` are left untouched either way.
"""

from __future__ import annotations

from typing import Any

from s2s_harness.models.state import EvaluationState, Suggestion
from s2s_harness.nodes._common import merge_suggestions

_CANDIDATE_FIELDS: tuple[str, ...] = (
    "candidate_error_clusters",
    "candidate_threshold_utility",
    "candidate_threshold_audio",
)


def _suggestions_from_side(side_result: Any) -> list[Suggestion]:
    side = side_result.side
    out: list[Suggestion] = []
    if side_result.best.strip():
        out.append(Suggestion(side=side, target="best", kind="tone", evidence=side_result.best))
    if side_result.worst.strip():
        out.append(Suggestion(side=side, target="worst", kind="tone", evidence=side_result.worst))
    for field_name in _CANDIDATE_FIELDS:
        for key in getattr(side_result, field_name):
            out.append(Suggestion(side=side, target=key, kind="tone", evidence=key))
    return out


async def interpret(state: EvaluationState) -> dict[str, Any]:
    try:
        from s2s_harness.llm.interpret import interpret as _llm_interpret
    except ImportError:
        return {}

    try:
        outcome = await _llm_interpret(state)
    except Exception:  # noqa: BLE001 - degrade, never block the graph
        return {}

    if outcome.value is None:
        return {}

    proposed = _suggestions_from_side(outcome.value.a) + _suggestions_from_side(outcome.value.b)
    if not proposed:
        return {}

    return {"suggestions": merge_suggestions(state.suggestions, proposed)}
