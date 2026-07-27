"""`render` {GRAPH-9}.

Reads: everything. Writes: nothing -- side effects only. Not LLM.

Terminal node. Formatting for a requested sink (CLI Rich output, `--json`
dump, bridge response) is CLI-*/BRIDGE-* territory; this node's job in
the graph is simply to be the place every path (Track A alone, Track A
plus a fully degraded Track B, or both tracks succeeding) converges
before `END`, without ever mutating `EvaluationState`. Returns an empty
update deliberately -- "never changes state" is enforced by returning
nothing to merge, not by convention alone.
"""

from __future__ import annotations

from typing import Any

from s2s_harness.models.state import EvaluationState


def render(state: EvaluationState) -> dict[str, Any]:
    return {}
