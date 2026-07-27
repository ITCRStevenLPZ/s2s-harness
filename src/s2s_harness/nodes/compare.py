"""`compare`. Track B node, new this wave -- no `GRAPH-n` id yet (posted
to T5 in `team_findings.md` [T3] for `docs/GRAPH_SPEC.md`; proposed
`{GRAPH-19}`). "Disagreement between tracks is the product, not a bug"
(team_plan.md) -- this node is what makes that visible.

Reads: `verdict` (Track A) and, when the field exists, `llm_verdict`
(Track B). Writes: an `info`-severity `Finding` recording agreement or
disagreement and -- only when the field exists -- `track_agreement`.

**Blocked on the same schema gap as `judge`** (`team_findings.md` [T3]
"BLOCKED item"): without a persisted `llm_verdict` field, this node has
no way to receive Track B's verdict from `judge` -- state is the only
contract between nodes (team_plan.md constraints), and an unregistered
dict key returned by one node does not survive to the next (verified
empirically, LangGraph drops unknown keys rather than passing them
through as a transient channel). So today this node honestly reports
"comparison unavailable" instead of fabricating a result. The moment
`nodes._common.HAS_LLM_VERDICT_FIELDS` is true, the real comparison
activates with no further code change here.
"""

from __future__ import annotations

from typing import Any

from s2s_harness.models.state import EvaluationState, Finding
from s2s_harness.nodes._common import HAS_LLM_VERDICT_FIELDS, HAS_TRACK_AGREEMENT_FIELD


def _unavailable_finding(reason: str) -> Finding:
    return Finding(
        severity="info",
        code="TRACK_COMPARE_UNAVAILABLE",
        label="COMPARE",
        message=(
            "Track A/B comparison unavailable: " + reason + ". See team_findings.md "
            "[T3] 'BLOCKED item' -- EvaluationState needs an llm_verdict field."
        ),
    )


def _agreement_finding(agree: bool, a_overall: str | None, b_overall: str) -> Finding:
    code = "TRACK_COMPARE_AGREE" if agree else "TRACK_COMPARE_DISAGREE"
    message = f"Track A picked {a_overall}; Track B's judge picked {b_overall}. " + (
        "The two agree." if agree else "The two disagree -- surfaced, not resolved."
    )
    return Finding(severity="info", code=code, label="COMPARE", message=message)


def compare(state: EvaluationState) -> dict[str, Any]:
    if not HAS_LLM_VERDICT_FIELDS:
        return {"findings": [*state.findings, _unavailable_finding("no llm_verdict field yet")]}

    llm_verdict = getattr(state, "llm_verdict", None)
    if llm_verdict is None:
        return {
            "findings": [
                *state.findings,
                _unavailable_finding("Track B's judge did not produce a verdict this run"),
            ]
        }

    a_overall = state.verdict.overall if state.verdict is not None else None
    agree = a_overall == llm_verdict.overall
    update: dict[str, Any] = {
        "findings": [*state.findings, _agreement_finding(agree, a_overall, llm_verdict.overall)]
    }
    if HAS_TRACK_AGREEMENT_FIELD:
        update["track_agreement"] = agree
    return update
