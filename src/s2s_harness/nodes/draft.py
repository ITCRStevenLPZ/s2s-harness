"""`draft` {GRAPH-7}.

Reads: everything. Writes: `draft`. Not LLM.

Wraps `rules.draft.build_draft(state, verdict) -> str` (note: the public
function is `build_draft`, not `draft` -- `team_findings.md` [lead]).
Always produces a complete string; this is the deterministic output
that satisfies the `--no-llm` guarantee on its own, before Track B is
ever consulted. Must run after `audit` -- `state.findings` is part of
`build_draft`'s input per RULES_SPEC section 5.
"""

from __future__ import annotations

from typing import Any

from s2s_harness.models.state import EvaluationState
from s2s_harness.rules.draft import build_draft as _build_draft


def draft(state: EvaluationState) -> dict[str, Any]:
    if state.verdict is None:
        raise ValueError("draft node requires state.verdict; decide must run first")
    return {"draft": _build_draft(state, state.verdict)}
