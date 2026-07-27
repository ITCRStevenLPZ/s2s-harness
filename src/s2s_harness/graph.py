"""The S2S Arena harness graph: topology, edge predicates and
checkpointing.

Base topology is `{GRAPH-10}` (`docs/GRAPH_SPEC.md` section 3),
implemented exactly as specified for Track A. Extended this wave for the
dual-track architecture (CLAUDE.md design rules 1/2, amended; owner
rejected the single-call-site design -- team_plan.md): Track A always
runs to completion (`ingest` through `draft`) before Track B is ever
consulted, and Track B (`interpret` -> `suggest` -> `judge` -> `compare`
-> `polish`) is skipped as a single unit when `llm_enabled` is `False`.

Why Track A -> Track B is sequential, not parallel, is recorded in full
in `.claude/team-runs/2026-07-27-wave3b-dual-track/team_findings.md`
[T3] "Design decision: Track A -> Track B sequential, not parallel
(with proof)" -- short version: `EvaluationState` (frozen this wave) has
no `Annotated` reducers, and two nodes writing the same field
(`suggestions`, `findings`) in the same LangGraph superstep raises
`InvalidUpdateError` (reproduced empirically). Sequential execution
needs no reducer and trivially preserves the `--no-llm` guarantee: by
the time Track B's gate is even evaluated, Track A's `verdict`,
`findings` and `draft` are already complete and untouched by anything
that follows.

Routing lives here, in one file, per the constraints in the dispatch
message ("Edges and routing live in one file"). No node decides where
the graph goes next by side effect; every edge below is a plain,
deterministic function of `EvaluationState`.

**Why `StateGraph` is declared over a `TypedDict` (`GraphState`), not
`EvaluationState` directly** -- reproduced and diagnosed empirically,
recorded in full in `team_findings.md` [T3] "CRITICAL: LangGraph's
Pydantic-schema reconstruction collides with `_reject_derived_on_input`":
LangGraph reconstructs the full state object via the schema's own
constructor (`schema(**merged_channels)`) before every node call. When
the schema is the `EvaluationState` Pydantic model, that reconstruction
re-runs every nested model's "after" validators on each step --
including `SideObservation._reject_derived_on_input` -- even though the
nested `SideObservation` instance was already validated once and
carries derived fields only through the sanctioned `with_derived()`
path. Pydantic's `revalidate_instances="never"` does not suppress this
(verified: "after" validators re-run on nested instances regardless of
that setting, reproduced with a minimal repro outside this codebase
entirely). Concretely: any run that reaches `normalize` and then a
second node afterward crashes with `_reject_derived_on_input`'s
`ValueError`, on every single golden fixture, because LangGraph cannot
pass `context={"allow_derived_fields": True}` through its own
`schema(**input)` reconstruction call -- only `model_validate(...,
context=...)` accepts a context, and LangGraph does not use that path.

This is a genuine incompatibility between `models/state.py`'s fail-closed
guard (correct and not to be weakened -- it is exactly right for
`ingest`'s real external-payload boundary) and LangGraph's per-step
Pydantic reconstruction (a framework mechanic, not something `models/`
was designed against). Fix applied entirely within this file (no edit to
`models/state.py`): `StateGraph(GraphState)` where `GraphState` is a
`TypedDict` mirroring `EvaluationState`'s fields field-for-field.
`TypedDict` is a typing construct only -- LangGraph never validates or
reconstructs it, so the derived-field guard is never re-triggered
between steps. Every node module in `s2s_harness.nodes` is unchanged and
still receives a genuine `EvaluationState` instance as `state`; `_typed`
/ `_typed_async` below do the one-line `EvaluationState.model_construct(
**mapping)` translation at graph-registration time, using
`model_construct` (the same "already trusted, skip validation" mechanism
`with_derived`'s own `model_copy` relies on) rather than the validating
constructor. `ingest`'s own validation boundary (the true external-input
edge) is unaffected -- it runs once, before `graph.invoke()`/`.ainvoke()`
is ever called, via `EvaluationState.model_validate(...)` at the CLI/
bridge call site, which is a different code path from the one this fix
touches.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from s2s_harness.models.state import EvaluationState
from s2s_harness.nodes.audit import audit as node_audit
from s2s_harness.nodes.compare import compare as node_compare
from s2s_harness.nodes.decide import decide as node_decide
from s2s_harness.nodes.draft import draft as node_draft
from s2s_harness.nodes.ingest import ingest as node_ingest
from s2s_harness.nodes.interpret import interpret as node_interpret
from s2s_harness.nodes.judge import judge as node_judge
from s2s_harness.nodes.normalize import normalize as node_normalize
from s2s_harness.nodes.polish import polish as node_polish
from s2s_harness.nodes.render import render as node_render
from s2s_harness.nodes.scan import scan as node_scan
from s2s_harness.nodes.suggest import suggest as node_suggest
from s2s_harness.nodes.transcribe import transcribe as node_transcribe

_CHECKPOINT_DB_PATH = Path(".s2s-cache") / "checkpoints.db"


class GraphState(TypedDict):
    """LangGraph's channel schema. Field-for-field identical to
    `EvaluationState` (models/state.py, STATE-17) -- kept as a
    structural mirror, not a redesign, so it never drifts silently: any
    field added to `EvaluationState` and not here will simply not be
    tracked as a channel, which is a loud, obvious failure (the field
    disappears from every node's reconstructed state) rather than a
    quiet one. See the module docstring for why this exists instead of
    using `EvaluationState` itself as the schema.
    """

    context: Any
    a: Any
    b: Any
    picks: Any
    audio_inputs: Any
    transcripts: Any
    suggestions: Any
    verdict: Any
    findings: Any
    draft: str
    polished: str
    llm_enabled: bool
    llm_skipped_reason: str


_SyncNode = Callable[[EvaluationState], dict[str, Any]]
_AsyncNode = Callable[[EvaluationState], Awaitable[dict[str, Any]]]
_Predicate = Callable[[EvaluationState], bool]


def _as_state(mapping: GraphState) -> EvaluationState:
    """Reconstruct a real `EvaluationState` from the channel mapping
    LangGraph hands a node, without re-running validation (see module
    docstring). Every value in `mapping` is already a validated /
    sanctioned-derivation instance -- `model_construct` trusts that,
    exactly like `SideObservation.with_derived()`'s own `model_copy`
    already does one layer down.
    """
    return EvaluationState.model_construct(**mapping)


def _typed(fn: _SyncNode) -> Callable[[GraphState], dict[str, Any]]:
    def wrapped(mapping: GraphState) -> dict[str, Any]:
        return fn(_as_state(mapping))

    return wrapped


def _typed_async(fn: _AsyncNode) -> Callable[[GraphState], Awaitable[dict[str, Any]]]:
    async def wrapped(mapping: GraphState) -> dict[str, Any]:
        return await fn(_as_state(mapping))

    return wrapped


def _typed_predicate(fn: _Predicate) -> Callable[[GraphState], bool]:
    def wrapped(mapping: GraphState) -> bool:
        return fn(_as_state(mapping))

    return wrapped


# ---------------------------------------------------------------------------
# Edge predicates -- deterministic checks over typed state, {GRAPH-11}
# extended. Every predicate is a pure function of `EvaluationState`; none
# of them import `s2s_harness.llm` or do I/O. Defined against the real
# model (not `GraphState`) so they stay independently testable exactly as
# GRAPH_SPEC intends; `_typed_predicate` adapts them for registration.
# ---------------------------------------------------------------------------


def has_audio(state: EvaluationState) -> bool:
    """Referenced by name in `{GRAPH-10}`'s conditional edge, never
    defined there. Predicate over `state.audio_inputs` being non-empty
    (`team_findings.md` [lead])."""
    return bool(state.audio_inputs)


def should_run_track_b(state: EvaluationState) -> bool:
    """New this wave (proposed `{GRAPH-20}`, see team_findings.md [T3]).
    Gates the entire Track B sub-chain as one unit: `interpret`,
    `suggest`, `judge`, `compare` and (subject to its own further gate
    below) `polish` all sit behind this single check. `--no-llm` /
    `llm_enabled=False` means none of Track B's imports are even
    attempted.
    """
    return bool(state.llm_enabled)


def should_polish(state: EvaluationState) -> bool:
    """`{GRAPH-11}`. True means "enter the `polish` node"; the node
    itself relays whatever cache-hit / exception / empty-response
    outcome its LLM call reports (see `nodes/polish.py`'s docstring for
    the reconciliation of GRAPH-8's four skip conditions against
    GRAPH-9's "render never changes state"). False means: `llm_enabled`
    is already known `False` by the time we would reach here (redundant
    with `should_run_track_b`, kept for GRAPH_SPEC-literal fidelity and
    independent testability), any finding is `error`-severity (do not
    spend tokens on a justification that should not be submitted), or
    `verdict.overall is None`.
    """
    if not state.llm_enabled:
        return False
    if any(finding.severity == "error" for finding in state.findings):
        return False
    if state.verdict is None or state.verdict.overall is None:
        return False
    return True


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def _assemble() -> StateGraph[GraphState, Any, Any, Any]:
    """Build the uncompiled graph: every node and every edge, exactly
    once. Shared by `build_graph()` and `compile_graph()` so the topology
    is defined in a single place, per the "routing lives in one file"
    constraint.
    """
    graph: StateGraph[GraphState, Any, Any, Any] = StateGraph(GraphState)

    # `# type: ignore[call-overload]` on every `add_node` call below:
    # reproduced in isolation outside this codebase -- mypy's overload
    # resolution for `StateGraph.add_node` fails to match a `Callable[[GS],
    # dict[str, Any]]` against its `_Node[NodeInputT]` protocol whenever the
    # callable's body calls a second function that also takes the same
    # `TypedDict` type as a parameter (a one-line node calling no helper
    # type-checks fine; the exact same node calling `_as_state` does not).
    # Confirmed at runtime this is a mypy-only false positive, not a real
    # type error: the golden-equivalence proof
    # (team_findings.md [T3] "Prove Track A ...") runs every node through
    # this exact graph and produces byte-identical output to calling the
    # underlying `rules/` functions directly.
    graph.add_node("ingest", _typed(node_ingest))  # type: ignore[call-overload]
    graph.add_node("transcribe", _typed(node_transcribe))  # type: ignore[call-overload]
    graph.add_node("scan", _typed(node_scan))  # type: ignore[call-overload]
    graph.add_node("normalize", _typed(node_normalize))  # type: ignore[call-overload]
    graph.add_node("decide", _typed(node_decide))  # type: ignore[call-overload]
    graph.add_node("audit", _typed(node_audit))  # type: ignore[call-overload]
    graph.add_node("draft", _typed(node_draft))  # type: ignore[call-overload]
    graph.add_node("interpret", _typed_async(node_interpret))  # type: ignore[call-overload]
    graph.add_node("suggest", _typed_async(node_suggest))  # type: ignore[call-overload]
    graph.add_node("judge", _typed_async(node_judge))  # type: ignore[call-overload]
    graph.add_node("compare", _typed(node_compare))  # type: ignore[call-overload]
    graph.add_node("polish", _typed_async(node_polish))  # type: ignore[call-overload]
    graph.add_node("render", _typed(node_render))  # type: ignore[call-overload]

    # Track A -- {GRAPH-10}, implemented exactly, through `draft`.
    graph.add_edge(START, "ingest")
    graph.add_conditional_edges(
        "ingest", _typed_predicate(has_audio), {True: "transcribe", False: "scan"}
    )
    graph.add_edge("transcribe", "scan")
    graph.add_edge("scan", "normalize")
    graph.add_edge("normalize", "decide")
    graph.add_edge("decide", "audit")
    graph.add_edge("audit", "draft")

    # Track B -- new this wave, sequential (see module docstring for why).
    graph.add_conditional_edges(
        "draft", _typed_predicate(should_run_track_b), {True: "interpret", False: "render"}
    )
    graph.add_edge("interpret", "suggest")
    graph.add_edge("suggest", "judge")
    graph.add_edge("judge", "compare")
    graph.add_conditional_edges(
        "compare", _typed_predicate(should_polish), {True: "polish", False: "render"}
    )
    graph.add_edge("polish", "render")

    graph.add_edge("render", END)
    return graph


def build_graph() -> CompiledStateGraph[GraphState, Any, Any, Any]:
    """Compile the graph without a checkpointer -- fine for a one-shot,
    non-`--resume` run, and what the golden-equivalence proof below
    uses. See `compile_graph()` for the checkpointed entry point CLI-*/
    BRIDGE-* should call instead.
    """
    return _assemble().compile()


def compile_graph(checkpointer: Any = None) -> CompiledStateGraph[GraphState, Any, Any, Any]:
    """The entry point CLI-*/BRIDGE-* should call. `checkpointer=None`
    behaves exactly like `build_graph()`; otherwise pass the result of
    `memory_checkpointer()` or `sqlite_checkpointer()` below.
    """
    if checkpointer is None:
        return _assemble().compile()
    return _assemble().compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Checkpointing -- {GRAPH-12}, {GRAPH-13}
# ---------------------------------------------------------------------------


def memory_checkpointer() -> MemorySaver:
    """A single CLI run, per `{GRAPH-12}`. Thread id = the run id, chosen
    by the caller (CLI-*) when invoking the compiled graph via
    `config={"configurable": {"thread_id": run_id}}`.
    """
    return MemorySaver()


async def sqlite_checkpointer(db_path: Path | None = None) -> Any:
    """Behind `--resume`, per `{GRAPH-12}`. `.s2s-cache/checkpoints.db` by
    default. **`async def`, not `def`** -- two real bugs found and fixed
    here in sequence while proving this function end to end (not just
    type-checked), both worth recording so they are not reintroduced:

    1. First cut returned `SqliteSaver.from_conn_string(str(path))`
       directly. That classmethod returns a context manager
       (`Iterator[SqliteSaver]`, meant for `with ... as saver:`), not a
       saver -- `compile_graph(checkpointer=<that context manager>)`
       would compile against an object that does not implement the
       checkpointer protocol at all. Would not have failed until
       `--resume` was actually exercised at runtime.
    2. Fixing (1) by constructing `SqliteSaver(conn)` directly (its own
       public, non-context-manager constructor) still breaks: this
       graph runs via `.ainvoke()` (Track B's four LLM-role nodes are
       coroutines), and the synchronous `SqliteSaver`'s async methods
       (`aget_tuple`, etc.) unconditionally raise `NotImplementedError`
       ("Consider using AsyncSqliteSaver instead") -- confirmed by
       actually running a fixture through `compile_graph(checkpointer=
       SqliteSaver(...))` with `.ainvoke()`, not just importing it.
       `AsyncSqliteSaver` is the correct type; its `__init__` calls
       `asyncio.get_running_loop()` unconditionally, so it can only be
       constructed inside a running event loop -- which is why this
       function is now `async def` rather than `def`. Callers (CLI-*)
       must `await sqlite_checkpointer(...)` from inside their own
       `async def` entry point (already true here -- the graph itself
       is only ever driven via `.ainvoke()`).

    `aiosqlite` (an `AsyncSqliteSaver` runtime dependency, distinct from
    `langgraph-checkpoint-sqlite` itself) resolves as a transitive
    dependency in this environment; if that ever stops being true in a
    fresh install, add it to `pyproject.toml` alongside
    `langgraph-checkpoint-sqlite` (flagged in team_findings.md [T3]).
    """
    try:
        import aiosqlite
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    except ImportError as exc:
        raise RuntimeError(
            "langgraph-checkpoint-sqlite / aiosqlite is not installed; "
            "--resume requires both (should be declared in pyproject.toml "
            "-- see team_findings.md [T3])."
        ) from exc

    path = db_path if db_path is not None else _CHECKPOINT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(str(path))
    return AsyncSqliteSaver(conn)
