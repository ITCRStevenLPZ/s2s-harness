"""`ingest` {GRAPH-1}.

Reads: caller payload. Writes: `context`, `a`, `b`, `picks`,
`audio_inputs`.

By the time any node runs, LangGraph has already coerced whatever the
caller passed into `graph.invoke()` / `graph.ainvoke()` through the
`EvaluationState` Pydantic schema (verified empirically, see
`team_findings.md` [T3] "Verified empirically: LangGraph 1.2.9 +
Pydantic state mechanics"): a plain `dict` with only `context`/`a`/`b`
keys set is filled out with every other field's default before node 1
ever executes. That is what makes "a malformed state never reaches
`decide`" true -- the raise happens at that coercion step, before the
graph body runs at all.

Reconciling GRAPH_SPEC's "accepts three payload shapes" (CLI interactive
answers, a JSON body from the bridge, a saved-run file being replayed)
with that mechanic: shaping each of those three into the `context` / `a`
/ `b` / `picks` / `audio_inputs` keys `EvaluationState` expects is CLI-*
/ BRIDGE-* work that happens *before* `graph.invoke()` is called, not
inside this node -- there is no earlier point in the graph for it to
happen. The replay case additionally needs
`context={"allow_derived_fields": True}` (`_reject_derived_on_input`,
`models/state.py`) when reconstructing an already-normalized
`SideObservation`; that context can only be supplied at the
`SideObservation.model_validate(...)` call site itself (CLI/bridge),
since LangGraph's own coercion path does not accept a validation
context. `ingest` never passes that context for anything -- doing so
here would blindly trust whatever shape arrived, silently disabling the
fail-closed guard for raw rater input (team_findings.md [lead], trap 2).

Given that, `ingest`'s job at the node level is a thin, explicit
boundary: name exactly the fields GRAPH_SPEC says this node writes, and
nothing else, even though every one of them already holds a valid value
by construction. Kept as its own node (rather than folded away) because
the graph topology should show where state enters, not leave it
implicit.
"""

from __future__ import annotations

from typing import Any

from s2s_harness.models.state import EvaluationState


def ingest(state: EvaluationState) -> dict[str, Any]:
    return {
        "context": state.context,
        "a": state.a,
        "b": state.b,
        "picks": state.picks,
        "audio_inputs": state.audio_inputs,
    }
