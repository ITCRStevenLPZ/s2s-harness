"""`decide` {GRAPH-5}.

Reads: `a`, `b`, `picks`. Writes: `verdict`. Not LLM.

Wraps `rules.decide.decide(a, b, picks) -> Verdict` ({RULE-10} through
{RULE-15}), Track A's threshold gate and hierarchy walk. Must run after
`normalize` -- it reads each side's derived `threshold_all`.
"""

from __future__ import annotations

from typing import Any

from s2s_harness.models.state import EvaluationState
from s2s_harness.rules.decide import decide as _decide


def decide(state: EvaluationState) -> dict[str, Any]:
    return {"verdict": _decide(state.a, state.b, state.picks)}
