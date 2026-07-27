"""Bridges `cli/` to the deterministic node pipeline and (opportunistically)
the compiled graph.

Layering (`docs/ARCHITECTURE.md`): "`cli/`, `bridge/` may import `nodes/`
and `models/`... may not import `rules/` directly -- go through the graph."
Every graph-or-node-facing call in this module goes through that same
narrow door: `s2s_harness.nodes` (never `s2s_harness.rules` directly) and,
best-effort, `s2s_harness.graph`.

Two paths, in preference order, both real and both exercised:

1. `s2s_harness.graph.compile_graph().ainvoke(...)` -- the full topology
   (`docs/GRAPH_SPEC.md` §3 plus this wave's Track B extension):
   checkpointing, `--resume`, `transcribe`, Track B, polish-cache.
   Preferred when it works.
2. A direct node pipeline (`_run_track_a_nodes` / `_try_track_b` below),
   calling the same node functions `graph.py` wires into the topology
   (`nodes.normalize -> nodes.decide -> nodes.audit -> nodes.draft`, then
   best-effort `nodes.judge`), just without LangGraph's own state
   coercion between steps.

Path (1) is currently broken for **any** multi-node run, including plain
Track A with `--no-llm` -- verified empirically and reported in
`team_findings.md` [T4] "VERIFIED, build-blocking": LangGraph's
`_coerce_state` reconstructs a bare `EvaluationState(**merged_dict)` at
every internal node boundary, which re-triggers
`SideObservation._reject_derived_on_input` the moment `normalize` has run,
because that guard has no way to know this reconstruction is internal
graph plumbing rather than raw caller input. That bug lives in
`graph.py`/`models/state.py`, both outside this package's ownership this
wave -- `run_graph_for_state` below tries path (1) first and falls back
to path (2) on any exception, so every CLI command still completes today,
and the moment that bug is fixed, path (1) starts winning with no change
needed here.

`s2s audit` always uses the direct node pipeline and stops after
`nodes.audit` -- `docs/CLI_SPEC.md` §`s2s audit`: "reports findings
without regenerating the draft." It has no reason to touch the compiled
graph, working or not.

`--resume` / checkpointing (`{GRAPH-12}`) only exists through path (1);
under path (2) it raises `EngineUnavailableError` rather than silently
ignoring `--resume` -- a rater who asked to resume a checkpoint should
not get a fresh, un-resumed run without being told.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from s2s_harness.cli.dual_track import Agreement, Confidence, TrackBResult
from s2s_harness.cli.errors import EngineUnavailableError
from s2s_harness.models.state import EvaluationState, Pick, Suggestion
from s2s_harness.nodes._common import HAS_LLM_VERDICT_FIELDS
from s2s_harness.nodes.audit import audit as _audit_node
from s2s_harness.nodes.decide import decide as _decide_node
from s2s_harness.nodes.draft import draft as _draft_node
from s2s_harness.nodes.normalize import normalize as _normalize_node
from s2s_harness.nodes.scan import scan as _scan_node

_VALID_PICKS = ("A", "B", "TIE", "BAD")

# The one and only producer of this message shape is `nodes/judge.py`'s
# `_judge_finding`. Parsing it is a stopgap for a verified schema gap
# (`team_findings.md` [T3] "BLOCKED item", confirmed independently in
# [T4]): `EvaluationState` has no `llm_verdict` field yet, so the Finding
# this node always appends on success is Track B's only durable channel.
# Delete this regex and `_track_b_from_finding` the moment
# `HAS_LLM_VERDICT_FIELDS` is true; `_extract_track_b` already prefers the
# real fields whenever they exist, so no caller needs to change.
_JUDGE_FINDING_RE = re.compile(
    r"^Track B judge picked (?P<overall>\S+) on (?P<driver>.+?) "
    r"\(confidence (?P<confidence>[\d.]+)\): (?P<reasoning>.*)$"
)


@dataclass(frozen=True)
class RunResult:
    state: EvaluationState
    track_b: TrackBResult | None
    agreement: Agreement
    used_compiled_graph: bool


def new_run_id() -> str:
    import uuid

    return uuid.uuid4().hex[:12]


def scan_for_state(state: EvaluationState) -> list[Suggestion]:
    """Scanner call for the interactive suggestion step, `{GRAPH-3}`.

    `nodes.scan` is a thin wrapper over `rules.scanner.scan`, both landed,
    synchronous and stable -- this is real, not a stand-in.
    """
    update = _scan_node(state)
    return cast(list[Suggestion], update["suggestions"])


def _run_track_a_nodes(state: EvaluationState, *, include_draft: bool) -> EvaluationState:
    """`normalize -> decide -> audit[-> draft]`, calling the same node
    functions `graph.py` wires into the topology, in the same order
    (`docs/GRAPH_SPEC.md` §3). `state.model_copy(update=...)` between
    steps, never re-validated -- this is what makes this path immune to
    the coercion bug documented in the module docstring. Zero LLM, zero
    network -- this is Track A.
    """
    state = state.model_copy(update=_normalize_node(state))
    state = state.model_copy(update=_decide_node(state))
    state = state.model_copy(update=_audit_node(state))
    if include_draft:
        state = state.model_copy(update=_draft_node(state))
    return state


def _bucket_confidence(value: float) -> Confidence:
    if value >= 0.75:
        return "high"
    if value >= 0.4:
        return "medium"
    return "low"


def _track_b_from_finding(state: EvaluationState) -> TrackBResult | None:
    for finding in reversed(state.findings):
        if finding.code != "LLM_JUDGE_VERDICT":
            continue
        match = _JUDGE_FINDING_RE.match(finding.message)
        if not match:
            return None
        overall_raw = match.group("overall")
        overall = cast(Pick, overall_raw) if overall_raw in _VALID_PICKS else None
        return TrackBResult(
            verdict=overall,
            driver=match.group("driver"),
            reasoning=match.group("reasoning"),
            confidence=_bucket_confidence(float(match.group("confidence"))),
        )
    return None


def _extract_track_b(state: EvaluationState) -> TrackBResult | None:
    """Prefers real `llm_verdict`/`llm_reasoning`/`llm_confidence` fields
    the moment they exist (`nodes/_common.HAS_LLM_VERDICT_FIELDS`); falls
    back to parsing `judge`'s own Finding until then. Either way, this is
    the one place that turns whatever Track B managed to leave in `state`
    into the CLI's `TrackBResult`.
    """
    if HAS_LLM_VERDICT_FIELDS:
        llm_verdict = getattr(state, "llm_verdict", None)
        if llm_verdict is None:
            return None
        return TrackBResult(
            verdict=llm_verdict.overall,
            driver=llm_verdict.driver,
            reasoning=getattr(state, "llm_reasoning", ""),
            confidence=_bucket_confidence(float(getattr(state, "llm_confidence", 0.0))),
        )
    return _track_b_from_finding(state)


async def _try_track_b_async(state: EvaluationState) -> EvaluationState:
    """Best-effort Track B via `s2s_harness.nodes.judge` (an async node).

    Verified independently broken today, but safely so:
    `team_findings.md` [T4] "VERIFIED, non-blocking" -- `nodes/judge.py`
    calls the real `llm.judge.judge` with the wrong arity and degrades to
    `{}` inside its own `try/except`. This wrapper additionally guards the
    call itself (import errors, the same arity issue, or anything else)
    so a broken Track B integration can never take Track A down with it.
    """
    try:
        from s2s_harness.nodes.judge import judge as judge_node
    except ImportError:
        return state
    try:
        update = await judge_node(state)
    except Exception:  # Track B is best-effort, by design; never propagate
        return state
    if not update:
        return state
    return state.model_copy(update=update)


def run_audit_only(state: EvaluationState) -> EvaluationState:
    """`s2s audit FILE`, `{CLI-3}`: normalize -> decide -> audit, no draft,
    no Track B. Direct node pipeline only -- there is no reason to wait on
    the compiled graph for this command; it never touches `draft` or
    either LLM track in the first place.
    """
    return _run_track_a_nodes(state, include_draft=False)


def run_graph_for_state(
    state: EvaluationState,
    *,
    llm_enabled: bool,
    resume_id: str | None,
    checkpoint_dir: Path,
) -> RunResult:
    """Runs Track A always, Track B when `llm_enabled`. See module
    docstring for the two-path preference order and why path (1) falls
    back today.
    """
    state = state.model_copy(update={"llm_enabled": llm_enabled})
    compiled_result = _try_compiled_graph(state, resume_id=resume_id, checkpoint_dir=checkpoint_dir)
    if compiled_result is not None:
        return compiled_result
    return _run_via_nodes(state, llm_enabled=llm_enabled, resume_id=resume_id)


def _try_compiled_graph(
    state: EvaluationState, *, resume_id: str | None, checkpoint_dir: Path
) -> RunResult | None:
    try:
        from s2s_harness.graph import compile_graph, sqlite_checkpointer
    except ImportError:
        return None
    checkpointer = None
    if resume_id is not None:
        try:
            checkpointer = sqlite_checkpointer(checkpoint_dir / "checkpoints.db")
        except Exception:
            return None
    try:
        compiled = compile_graph(checkpointer=checkpointer)
        thread_id = resume_id or new_run_id()
        config = {"configurable": {"thread_id": thread_id}}
        result = asyncio.run(compiled.ainvoke(state, config=config))  # type: ignore[call-overload]
    except Exception:
        # Known-broken today (team_findings.md [T4]); fall back to the
        # direct node pipeline rather than failing the command.
        return None
    final_state = EvaluationState.model_validate(result, context={"allow_derived_fields": True})
    track_b = _extract_track_b(final_state)
    verdict_overall = final_state.verdict.overall if final_state.verdict else None
    return RunResult(
        state=final_state,
        track_b=track_b,
        agreement=Agreement.compute(verdict_overall, track_b),
        used_compiled_graph=True,
    )


def _run_via_nodes(
    state: EvaluationState, *, llm_enabled: bool, resume_id: str | None
) -> RunResult:
    if resume_id is not None:
        raise EngineUnavailableError(
            "--resume needs the compiled graph's checkpointer "
            "(s2s_harness.graph), which is not usable in this build yet "
            "(see team_findings.md [T4]); re-run without --resume"
        )
    state = _run_track_a_nodes(state, include_draft=True)
    if llm_enabled:
        state = asyncio.run(_try_track_b_async(state))
    track_b = _extract_track_b(state) if llm_enabled else None
    verdict_overall = state.verdict.overall if state.verdict else None
    agreement = Agreement.compute(verdict_overall, track_b)
    return RunResult(state=state, track_b=track_b, agreement=agreement, used_compiled_graph=False)
