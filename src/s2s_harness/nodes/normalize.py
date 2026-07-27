"""`normalize` {GRAPH-4}.

Reads: `a`, `b`, `context`. Writes: `a.threshold_*`, `b.threshold_*`,
`audio_penalized` (on each side, via `SideObservation.with_derived` --
see `rules/normalize.py`). Not LLM.

`rules.normalize.normalize(side, context) -> side` operates on one side
at a time; this node calls it once per side and returns both. Only this
node ever produces the update path that reaches `with_derived` for raw
rater input -- `ingest` never does (`team_findings.md` [lead], trap 4).
"""

from __future__ import annotations

from typing import Any

from s2s_harness.models.state import EvaluationState
from s2s_harness.rules.normalize import normalize as _normalize


def normalize(state: EvaluationState) -> dict[str, Any]:
    return {
        "a": _normalize(state.a, state.context),
        "b": _normalize(state.b, state.context),
    }
