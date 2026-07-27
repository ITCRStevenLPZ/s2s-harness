"""`audit` {GRAPH-6}.

Reads: everything. Writes: `findings`. Not LLM.

Wraps `rules.audit.audit(state, verdict) -> list[Finding]` ({RULE-16}
through {RULE-23}). Must run after `decide` -- `state.verdict` is
required and is not optional here; a `None` verdict at this point means
the graph topology was not respected (`decide` skipped), which is a
programming error, not a runtime condition to degrade from.
"""

from __future__ import annotations

from typing import Any

from s2s_harness.models.state import EvaluationState
from s2s_harness.rules.audit import audit as _audit


def audit(state: EvaluationState) -> dict[str, Any]:
    if state.verdict is None:
        raise ValueError("audit node requires state.verdict; decide must run first")
    return {"findings": _audit(state, state.verdict)}
