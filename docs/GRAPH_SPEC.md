# Graph specification

Version: 1.2.0
Last updated: 2026-07-27

**Wave 3b, second pass (this version):** T3 landed the graph (Phase C) and, in the process, hit a real framework incompatibility this spec did not anticipate — see the new note under §3 ({GRAPH-10}) and the deprecation of this document's opening line below. `StateGraph` is declared over a `GraphState` `TypedDict`, not `EvaluationState` directly; §4 ({GRAPH-12}) gains a note on the `langgraph-checkpoint-sqlite` dependency T5 added to make `SqliteSaver` actually importable. Both are additive corrections to a load-bearing implementation fact, not a design change — nothing about what the graph *does* changed, only what LangGraph is told its channel schema is. Full empirical diagnosis in `.claude/team-runs/2026-07-27-wave3b-dual-track/team_findings.md` [T3] "CRITICAL, found and fixed entirely within `graph.py`." Also this pass: §2 gains `judge` {GRAPH-18} and `compare` {GRAPH-19} node entries — IDs T3 proposed directly in those nodes' own module docstrings, folded in here now that Phase C landed them. `interpret`/`suggest` node wrappers exist too but are not yet covered; add when their own IDs are proposed the same way.

**Wave 3b, first pass:** corrected the node table's `polish` LLM column and the `polish` {GRAPH-8} section header, both of which asserted or implied `polish` is the graph's only LLM call site. That claim is superseded by CLAUDE.md design rule 2 (amended the same day) — LLM code now lives in `src/s2s_harness/llm/` with four roles. Nothing about `polish`'s own behavior below changed; the correction is scoped to the "only one" framing. The new `interpret`/`suggest`/`judge` nodes, the Track B branch, and the `compare` node are still not specified in this document as of the second pass either — they are real and landed (`src/s2s_harness/graph.py`, `src/s2s_harness/nodes/{interpret,suggest,judge,compare}.py`), but assigning them their own `GRAPH-n` IDs is T3's authorship call to make, not something to backfill from outside without their sign-off. The module docstring of `graph.py` is the authoritative description of that topology until T3 folds it in here.

**ID convention:** `STATE-n` tags each `Literal` alias and each model/class in §1, in document order, as a trailing comment on the class/alias line. `GRAPH-n` tags each node in §2 (one per row/description pair), the edge topology and `should_polish` predicate in §3, and — extending past the literal task scope because both are load-bearing requirements of this spec — checkpointing in §4 and the mode-difference table in §5. IDs are additive only; no model field, node behavior or edge was reworded, reordered or removed to add them.

LangGraph + Pydantic. State is a single validated model threaded through every node; nodes return partial updates. **Deprecated, second pass:** "threaded through every node" is no longer literally true of what LangGraph itself holds and reconstructs between steps — see the note under §3 ({GRAPH-10}) for why and what changed. Every node function's own signature is unaffected: each still receives and returns a real `EvaluationState`, and this document's §1/§2 describe that model exactly as before.

## 1. State schema

`src/s2s_harness/models/state.py`

```python
Side      = Literal["A", "B"]                      # STATE-1
Pick      = Literal["A", "B", "TIE", "BAD"]        # STATE-2  TIE = "Both Good", BAD = "Both Bad"
Mode      = Literal["conversation", "clips"]        # STATE-3
Noise     = Literal["clean", "slight", "notable"]   # STATE-4
Premise   = Literal["na", "pushback", "hedged", "accepted"]  # STATE-5
Success   = Literal["pass", "partial", "fail"]      # STATE-6
Severity  = Literal["error", "warning", "info", "ok"]  # STATE-7

ScenarioType = Literal[                             # STATE-8
    "standard", "redteam", "premise", "instruction",
    "interrupt", "emotional", "roleplay", "creative",
]
```

```python
# STATE-9
class SideObservation(BaseModel):
    side: Side
    notes: str = ""
    best: str = ""                       # strongest specific moment
    worst: str = ""                      # weakest specific moment
    error_clusters: list[str] = []       # keys from rules.catalog.ERROR_CLUSTERS
    threshold_utility: list[str] = []    # keys from rules.catalog.THRESHOLD_UTILITY
    threshold_audio: list[str] = []      # keys from rules.catalog.THRESHOLD_AUDIO
    background_noise: Noise = "clean"
    premise_handling: Premise = "na"
    turns: int | None = None             # conversation mode only
    task_success: Success | None = None  # conversation mode only

    # derived by `normalize`, never set by the caller
    threshold_all: list[str] = []
    audio_penalized: bool = False
```

```python
# STATE-10
class Preflight(BaseModel):          # conversation mode only
    headphones: bool = False
    panning_check: bool = False
    scenario_read: bool = False
    listened_isolated: bool = False
    equivalent_prompts: bool = False
    stayed_in_character: bool = False
    interruption_tested: bool = False

# STATE-11
class TaskContext(BaseModel):
    mode: Mode
    scenario: str = ""                   # conversation: the assigned scenario/persona
    prompt: str = ""                     # clips: the question the clips answer
    scenario_type: ScenarioType = "standard"
    ground_truth: str = ""               # clips: the fact, when the prompt embeds a false premise
    prompts_used: list[str] = []         # conversation: the turn prompts, for equivalence review
    preflight: Preflight = Preflight()
    skip_reason: str = ""                # non-empty ⇒ technical skip, not a vote

# STATE-12
class Picks(BaseModel):
    naturalness: Pick | None = None
    utility: Pick | None = None
    audio: Pick | None = None
    overall: Pick | None = None

# STATE-13
class Verdict(BaseModel):
    overall: Pick | None
    driver: str                          # human-readable deciding dimension
    gated: bool = False
    gated_side: Side | None = None       # the side that breached the threshold
    trace: list[str] = []                # ordered explanation of the walk

# STATE-14
class Finding(BaseModel):
    severity: Severity
    code: str                            # stable identifier, e.g. "AUDIO_BOTH_GOOD_ILLEGAL"
    label: str                           # short chip text, e.g. "AUDIO"
    message: str

# STATE-15
class Suggestion(BaseModel):
    side: Side
    target: str                          # catalog key the scanner matched
    kind: Literal["error_cluster", "threshold_utility", "threshold_audio", "tone"]
    evidence: str                        # the matched span from the notes

# STATE-17
class EvaluationState(BaseModel):
    context: TaskContext
    a: SideObservation
    b: SideObservation
    picks: Picks = Picks()
    audio_inputs: dict[str, Path] = {}   # {"a": ..., "b": ...} when dictating
    transcripts: dict[str, Transcript] = {}
    suggestions: list[Suggestion] = []
    verdict: Verdict | None = None
    findings: list[Finding] = []
    draft: str = ""                      # deterministic, always populated
    polished: str = ""                   # LLM output, may be empty
    llm_enabled: bool = True
    llm_skipped_reason: str = ""
```

### Transcript {STATE-16}

`Transcript` is **not** redefined here. It is the model already defined in `docs/STT_SPEC.md` §2 / `src/s2s_harness/stt/base.py`:

```python
class Word(BaseModel):
    text: str
    start_s: float | None = None
    end_s: float | None = None

class Transcript(BaseModel):
    text: str                # the rater's dictated notes, verbatim
    language: str | None = None
    words: list[Word] = []   # word-level timing, when the provider returns it
    provider: str             # which STT provider produced this transcript, for traceability
    duration_s: float | None = None
    raw: dict | None = None  # provider payload, debugging only
```

`state.py` imports `Transcript` from `src/s2s_harness/stt/base.py` rather than declaring a second model. `EvaluationState.transcripts` is keyed by side (`"a"` / `"b"`), matching the keys used in `audio_inputs`. Defining a second, divergent `Transcript` model in this file would be exactly the kind of drift the spec-ID retrofit exists to catch — see `STT-3` in `docs/STT_SPEC.md`.

Nodes return `dict` partial updates; LangGraph merges them. Only `normalize` may write derived fields on `SideObservation`. {STATE-18}

## 2. Nodes

| Node | Reads | Writes | LLM |
|---|---|---|---|
| `ingest` | caller payload | `context`, `a`, `b`, `picks`, `audio_inputs` | no |
| `transcribe` | `audio_inputs` | `transcripts`, appends to `a.notes` / `b.notes` | no (external STT API) |
| `scan` | `a.notes`, `b.notes` | `suggestions` | no |
| `normalize` | `a`, `b`, `context` | `a.threshold_*`, `b.threshold_*`, `audio_penalized` | no |
| `decide` | `a`, `b`, `picks` | `verdict` | no |
| `audit` | everything | `findings` | no |
| `draft` | everything | `draft` | no |
| `judge` | everything (Track B) | `findings` (`LLM_JUDGE_VERDICT`); `llm_verdict`/`llm_reasoning`/`llm_confidence` when the field exists | **yes** — see {GRAPH-18} |
| `compare` | `verdict`, `llm_verdict` when present | `findings` (`TRACK_COMPARE_AGREE`/`_DISAGREE`/`_UNAVAILABLE`); `track_agreement` when the field exists | no (reads Track B's output, makes no LLM call itself) |
| `polish` | `draft`, `findings`, state | `polished`, `llm_skipped_reason` | **yes** — deprecated note: this column previously read "yes — the only one," asserting `polish` was the sole LLM call site in the graph. That claim is superseded by CLAUDE.md design rule 2 (amended Wave 3b, 2026-07-27): `src/s2s_harness/llm/` now hosts four LLM roles (`interpret`, `suggest`, `judge`, `polish`). `polish` remains the only node that rewrites the draft's *text*; see CLAUDE.md rule 2 for the per-role contract, {GRAPH-18} for `judge`, and {GRAPH-19} for `compare`. `interpret`/`suggest` node rows are still pending — landed as role functions (`src/s2s_harness/llm/{interpret,suggest}.py`) but their node wrappers were not covered by this pass; add when their own `GRAPH-n` IDs are proposed the same way `judge`/`compare` were. |
| `render` | everything | side effects only | no |

### `ingest` {GRAPH-1}
Accepts three payload shapes and normalizes to `EvaluationState`: CLI interactive answers, a JSON body from the bridge, or a saved run file being replayed. Validation failures raise before the graph runs — a malformed state never reaches `decide`.

### `transcribe` {GRAPH-2}
Skipped unless `audio_inputs` is non-empty. Delegates to the configured provider (`docs/STT_SPEC.md`). Appends the transcript to the corresponding `notes` field rather than replacing it, so a rater can type a little and dictate the rest. Records `Transcript` with word offsets when the provider returns them.

### `scan` {GRAPH-3}
Runs the bilingual signal catalogue over each side's notes. Produces `Suggestion` objects; **never mutates flags**. Accepting a suggestion is an explicit caller action (CLI prompt, bridge click), matching the chip behavior in the HTML tools.

### `normalize` {GRAPH-4}
Pure derivation, in this order:
1. `background_noise == "notable"` → append `"notable, distracting background noise"` to `threshold_audio`.
2. `scenario_type in {"redteam", "premise"}` **and** `premise_handling == "accepted"` → append the false-claim acceptance key to `threshold_utility` if not already present.
3. `threshold_all = threshold_utility + threshold_audio`.
4. `audio_penalized = bool(threshold_audio)`.

### `decide` {GRAPH-5}
Implements `docs/RULES_SPEC.md` §3. Returns a `Verdict` with a populated `trace`. Deterministic, total (never raises), and returns `overall=None` only when Naturalness is unset.

### `audit` {GRAPH-6}
Implements `docs/RULES_SPEC.md` §4. Returns findings sorted `error → warning → info → ok`.

### `draft` {GRAPH-7}
Implements `docs/RULES_SPEC.md` §5. Always returns a complete string. Emits `【placeholder】` markers for missing rater observations.

### `polish` {GRAPH-8}
**Note (Wave 3b, 2026-07-27):** this section still describes only the `polish` node, which remains accurate for `polish` itself. It no longer describes the graph's *only* LLM node — `interpret`, `suggest` and `judge` are three more, specified by CLAUDE.md design rule 2 and pending their own `GRAPH-n` entries from T3's Phase C work. Nothing below this note is deprecated; it is simply no longer the whole LLM story.

Skipped, with `llm_skipped_reason` set, when any of:
- `llm_enabled` is `False` (`--no-llm`)
- any finding has `severity == "error"` (do not spend tokens on a justification that should not be submitted)
- `verdict.overall` is `None`
- a cache hit on `sha256(draft + mode + PROMPT_VERSION)`

Otherwise: one completion, system prompt from `criteria/`, user content = the draft plus the structured observations. Hard constraints in the prompt: use only supplied observations, invent nothing, preserve `【placeholders】` verbatim, return only the paragraph. On any exception or empty response, fall back to `draft` silently and note it in `llm_skipped_reason`.

### `render` {GRAPH-9}
Formats for the requested sink. Never changes state.

### `judge` (Track B) {GRAPH-18}
**Added Wave 3b, second pass** — T3 proposed this ID directly in `src/s2s_harness/nodes/judge.py`'s own module docstring ("no `GRAPH-n` id yet ... proposed `{GRAPH-18}`"), folded in here now that Phase C has landed. Reads the full state; wraps `s2s_harness.llm.judge.judge(state) -> JudgeOutcome` (§ "the four LLM roles", CLAUDE.md rule 2). On a value, always appends an `info`-severity `Finding` (`LLM_JUDGE_VERDICT`) recording Track B's competing verdict, driver, confidence and reasoning — this Finding is the durable record of Track B's opinion today. Never writes `state.verdict`, which stays Track A's alone (`team_plan.md`: "The rater submits. Default is Track A's verdict.").

**Known gap, not a bug:** `EvaluationState` has no typed field to hold Track B's verdict (`llm_verdict`/`llm_reasoning`/`llm_confidence`) — adding one requires editing `src/s2s_harness/models/state.py`, guarded off-limits for the whole team this wave regardless of file ownership. This node feature-detects the gap via `nodes._common.HAS_LLM_VERDICT_FIELDS` (`{"llm_verdict","llm_reasoning","llm_confidence"} <= EvaluationState.model_fields`) and writes those fields opportunistically only when a future wave adds them; until then the appended `Finding` is Track B's only durable trace, and `compare` below reports "unavailable" rather than fabricating a comparison. Full detail: `team_findings.md` [T3] "Three fixes after the team-lead gate check."

### `compare` {GRAPH-19}
**Added Wave 3b, second pass**, same provenance as `judge` above (T3 proposed `{GRAPH-19}` in `nodes/compare.py`'s own docstring). "Disagreement between tracks is the product, not a bug" (`team_plan.md`) — this is the node that makes it visible. Reads Track A's `verdict` and, when `HAS_LLM_VERDICT_FIELDS` is true, Track B's `llm_verdict`; appends an `info`-severity `Finding` (`TRACK_COMPARE_AGREE` / `TRACK_COMPARE_DISAGREE`) naming which side each track picked and whether they agree. Writes `track_agreement` only when `nodes._common.HAS_TRACK_AGREEMENT_FIELD` is true (same guarded-field gap as `judge`).

Today, since the gap is unclosed, this node cannot see `judge`'s output at all — LangGraph does not pass an unregistered dict key through as a transient channel (verified empirically) — so it appends an honest `TRACK_COMPARE_UNAVAILABLE` info Finding instead of guessing. The moment a future wave adds the `llm_verdict` field to `models/state.py`, the real comparison activates with no code change to this node.

## 3. Edges

```python
graph.add_edge(START, "ingest")
graph.add_conditional_edges("ingest", has_audio, {True: "transcribe", False: "scan"})
graph.add_edge("transcribe", "scan")
graph.add_edge("scan", "normalize")
graph.add_edge("normalize", "decide")
graph.add_edge("decide", "audit")
graph.add_edge("audit", "draft")
graph.add_conditional_edges("draft", should_polish, {True: "polish", False: "render"})
graph.add_edge("polish", "render")
graph.add_edge("render", END)
```
{GRAPH-10}

**Note added Wave 3b, second pass (2026-07-27), extending {GRAPH-10}:** `StateGraph` is not declared over `EvaluationState` directly. It is declared over `GraphState`, a `TypedDict` in `src/s2s_harness/graph.py` mirroring `EvaluationState` field-for-field. Reason, diagnosed empirically by T3: LangGraph reconstructs the full state object via the schema's own constructor (`schema(**merged_channels)`) before every node call, not just once at invocation. When the schema is the `EvaluationState` Pydantic model, that reconstruction re-runs every nested model's `model_validator(mode="after")` on each step — including `SideObservation._reject_derived_on_input` — even though the nested instance was already validated once and carries its derived fields only through the sanctioned `with_derived()` path. `revalidate_instances="never"` does not suppress this for nested field values. Concretely: any run reaching `normalize` and then a second node crashed with `_reject_derived_on_input`'s `ValueError`, on every fixture, because LangGraph's `schema(**input)` call cannot pass `context={"allow_derived_fields": True}` through — only `model_validate(..., context=...)` accepts a context, and LangGraph does not use that path.

This is a genuine incompatibility between `models/state.py`'s fail-closed guard (correct, and not weakened — it is exactly right for `ingest`'s real external-payload boundary) and a LangGraph framework mechanic nobody had exercised before Phase C. Fixed entirely within `graph.py`, with **zero edits to `models/state.py`** (guarded and off-limits for the whole team this wave regardless): `TypedDict` is a typing construct only, never validated or reconstructed by LangGraph, so the guard is never re-triggered between steps. Every node module in `s2s_harness.nodes` is unaffected — each still receives a genuine `EvaluationState` instance as `state` via a one-line `_as_state()` adapter (`EvaluationState.model_construct(**mapping)`, the same "already trusted" mechanism `with_derived()`'s own `model_copy` relies on) applied only at graph-registration time. `ingest`'s true external-payload validation boundary (`EvaluationState.model_validate(...)`, called by the CLI/bridge before `graph.invoke()`) is a different code path and is unaffected. Full empirical repro: `team_findings.md` [T3] "CRITICAL, found and fixed entirely within `graph.py`."

`should_polish` is a pure predicate over state — it encodes the skip conditions above so the decision is visible in the graph topology rather than buried in the node. {GRAPH-11}

## 4. Checkpointing

Use `MemorySaver` for a single CLI run and `SqliteSaver` (`.s2s-cache/checkpoints.db`) when `--resume` is available. Thread id = the run id. {GRAPH-12}

**Note added Wave 3b, second pass:** `SqliteSaver` ships in a separate distribution, `langgraph-checkpoint-sqlite`, not bundled with `langgraph` itself. Added to `pyproject.toml` as a core dependency (verified resolvable via `uv pip install --dry-run` before locking, not guessed — resolves `langgraph-checkpoint-sqlite==3.1.0`) rather than an extra, since `--resume` is a standard CLI capability per this section, not an optional external integration.

Why it matters here: the realistic loop is *evaluate → the audit flags a contradiction → the rater changes one pick → re-run*. With checkpointing plus draft-hash caching, that second pass re-executes only `decide`, `audit`, `draft` — all free — and reuses the polished prose if the draft text did not change. {GRAPH-13}

## 5. Mode differences {GRAPH-14}

Everything below is the complete list. Anything not listed is shared.

| Concern | `conversation` | `clips` |
|---|---|---|
| Vocabulary | "Model A" / "Model B" | "Clip A" / "Clip B" |
| Turn fields | required, min 4, must match | absent |
| Preflight block | required | not collected |
| Prompt equivalence check | required | n/a (single shared prompt) |
| Interruption-related clusters | available | replaced by `robotic_intonation`, `over_structured` |
| Task success | collected per side | not collected |
| Ground truth field | optional | prominent, drives premise findings |

Implement as two `catalog` profiles and two validator lists, selected by `context.mode`. Do not fork the engine. {GRAPH-15}
