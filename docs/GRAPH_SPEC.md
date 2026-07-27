# Graph specification

Version: 1.0.0
Last updated: 2026-07-26

**ID convention:** `STATE-n` tags each `Literal` alias and each model/class in §1, in document order, as a trailing comment on the class/alias line. `GRAPH-n` tags each node in §2 (one per row/description pair), the edge topology and `should_polish` predicate in §3, and — extending past the literal task scope because both are load-bearing requirements of this spec — checkpointing in §4 and the mode-difference table in §5. IDs are additive only; no model field, node behavior or edge was reworded, reordered or removed to add them.

LangGraph + Pydantic. State is a single validated model threaded through every node; nodes return partial updates.

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
| `polish` | `draft`, `findings`, state | `polished`, `llm_skipped_reason` | **yes — the only one** |
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
Skipped, with `llm_skipped_reason` set, when any of:
- `llm_enabled` is `False` (`--no-llm`)
- any finding has `severity == "error"` (do not spend tokens on a justification that should not be submitted)
- `verdict.overall` is `None`
- a cache hit on `sha256(draft + mode + PROMPT_VERSION)`

Otherwise: one completion, system prompt from `criteria/`, user content = the draft plus the structured observations. Hard constraints in the prompt: use only supplied observations, invent nothing, preserve `【placeholders】` verbatim, return only the paragraph. On any exception or empty response, fall back to `draft` silently and note it in `llm_skipped_reason`.

### `render` {GRAPH-9}
Formats for the requested sink. Never changes state.

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

`should_polish` is a pure predicate over state — it encodes the skip conditions above so the decision is visible in the graph topology rather than buried in the node. {GRAPH-11}

## 4. Checkpointing

Use `MemorySaver` for a single CLI run and `SqliteSaver` (`.s2s-cache/checkpoints.db`) when `--resume` is available. Thread id = the run id. {GRAPH-12}

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
