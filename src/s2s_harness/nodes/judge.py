"""`judge`. Track B role, new this wave -- no `GRAPH-n` id yet (posted to
T5 in `team_findings.md` [T3] for `docs/GRAPH_SPEC.md`; proposed
`{GRAPH-18}`).

Reads: the full state. Writes: an `info`-severity `Finding` recording
Track B's competing verdict, reasoning and confidence, and -- only when
the field exists (see below) -- `llm_verdict` / `llm_reasoning` /
`llm_confidence`.

Wraps `s2s_harness.llm.judge.judge(state) -> JudgeOutcome`.
`JudgeOutcome.value` is a `JudgeVerdict` (`overall`, `driver`,
`confidence`, `reasoning`, `gated`, `gated_side`) -- deliberately shaped
like `models.state.Verdict` but never written to `EvaluationState.verdict`,
per `llm/judge.py`'s own docstring: "a `judge_verdict`-shaped field is
T3's node/state design, outside this file's ownership."

**Blocked, worked around -- see `team_findings.md` [T3] "BLOCKED item"**:
`EvaluationState` (frozen this wave, no owner in `team_plan.md`'s
ownership table) has no field to hold Track B's verdict. This node
feature-detects `nodes._common.HAS_LLM_VERDICT_FIELDS`; when absent (the
situation today), the only durable record of Track B's opinion is the
`Finding` this node always appends, and `compare` cannot do a real
comparison (it says so explicitly, rather than guessing). Never
overwrites `state.verdict` -- that field is Track A's alone, per
team_plan.md: "The rater submits. Default is Track A's verdict.
Overriding with Track B's is explicit... Nothing auto-applies."
"""

from __future__ import annotations

from typing import Any

from s2s_harness.models.state import EvaluationState, Finding
from s2s_harness.nodes._common import HAS_LLM_VERDICT_FIELDS

_REASON_UNAVAILABLE = "provider_error"


def _judge_finding(overall: str, driver: str, confidence: float, reasoning: str) -> Finding:
    return Finding(
        severity="info",
        code="LLM_JUDGE_VERDICT",
        label="LLM JUDGE",
        message=(
            f"Track B judge picked {overall} on {driver} "
            f"(confidence {confidence:.2f}): {reasoning}"
        ),
    )


async def judge(state: EvaluationState) -> dict[str, Any]:
    try:
        from s2s_harness.llm.judge import judge as _llm_judge
    except ImportError:
        return {}

    try:
        outcome = await _llm_judge(state)
    except Exception:  # noqa: BLE001 - degrade, never block the graph
        return {}

    if outcome.value is None:
        return {}

    jv = outcome.value
    finding = _judge_finding(jv.overall, jv.driver, jv.confidence, jv.reasoning)
    update: dict[str, Any] = {"findings": [*state.findings, finding]}
    if HAS_LLM_VERDICT_FIELDS:
        from s2s_harness.models.state import Verdict

        update["llm_verdict"] = Verdict(
            overall=jv.overall, driver=jv.driver, gated=jv.gated, gated_side=jv.gated_side
        )
        update["llm_reasoning"] = jv.reasoning
        update["llm_confidence"] = jv.confidence
    return update
