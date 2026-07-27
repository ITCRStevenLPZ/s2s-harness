"""`polish` {GRAPH-8}. One of Track B's four LLM roles (CLAUDE.md design
rule 2, amended Wave 3b) -- still the only role that touches the
draft's *text*.

Reads: `draft`, `findings`, state. Writes: `polished`,
`llm_skipped_reason`.

Wraps `s2s_harness.llm.polish.polish(state, draft) -> PolishOutcome`
(T2, landed after this node was first drafted -- see
`team_findings.md` [T3] for the earlier, now-superseded assumed
contract). `PolishOutcome.text` is *always* populated -- T2's role
already applies CLAUDE.md design rule 3's fallback internally
(`polish.py`'s own `_gate_reason`: `llm_enabled is False`, any
`error`-severity finding, or `verdict.overall is None`, mirroring this
graph's `should_polish` edge predicate) plus its own exception / empty
-response / placeholder-dropped degradation. This node therefore does
almost no work of its own: relay `outcome.text` to `polished` and
`outcome.skipped_reason` to `llm_skipped_reason` verbatim.

`should_polish` (`graph.py`) still gates whether this node is entered at
all, per `{GRAPH-11}` and the "edge decided before the node runs"
constraint -- so the common case (llm disabled, blocking errors, no
verdict) never even reaches this node's own (redundant, and that is
fine -- defense in depth, not a contradiction) internal gate.

Falls back to the deterministic draft on any exception this node's own
call raises that `polish()` itself did not already catch (defence in
depth; T2's role is not expected to raise, but nothing here trusts that
absolutely).
"""

from __future__ import annotations

from typing import Any

from s2s_harness.models.state import EvaluationState

_REASON_UNAVAILABLE = "provider_error"


async def polish(state: EvaluationState) -> dict[str, Any]:
    try:
        from s2s_harness.llm.polish import polish as _llm_polish
    except ImportError:
        return {"polished": state.draft, "llm_skipped_reason": _REASON_UNAVAILABLE}

    try:
        outcome = await _llm_polish(state, state.draft)
    except Exception:  # noqa: BLE001 - last-resort backstop, mirrors client.py's own policy
        return {"polished": state.draft, "llm_skipped_reason": _REASON_UNAVAILABLE}

    return {"polished": outcome.text, "llm_skipped_reason": outcome.skipped_reason}
