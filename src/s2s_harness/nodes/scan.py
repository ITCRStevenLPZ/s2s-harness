"""`scan` {GRAPH-3}.

Reads: the whole state (per `rules/scanner.py`'s actual signature,
`scan(state) -> list[Suggestion]` -- the node table's "reads a.notes /
b.notes" is imprecise, see `team_findings.md` [lead]). Writes:
`suggestions`. Not LLM.

Thin wrapper: no signal detection happens here, only marshalling.
`suggest` (Track B) later merges its own `Suggestion[]` into this same
field via `nodes/_common.merge_suggestions`; this node's output is what
that merge starts from.
"""

from __future__ import annotations

from typing import Any

from s2s_harness.models.state import EvaluationState
from s2s_harness.rules.scanner import scan as _scan


def scan(state: EvaluationState) -> dict[str, Any]:
    return {"suggestions": _scan(state)}
