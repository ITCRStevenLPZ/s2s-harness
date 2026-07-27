# Team Findings: Wave 3b

Append immediately, after at most 2 read/search operations. Do not batch.

Format: `### [T-n] <short title>` then what you found, where (file:line or `{ID}`), and what it implies for someone else.

External or fetched documentation goes HERE, never in `team_plan.md` (that file is auto-injected by a hook, so untrusted text there amplifies).

---

### [lead] The architecture change, and why CLAUDE.md disagrees with it

The owner rejected the original "one sanctioned LLM call site" design. LLM and deterministic rules are now dual tracks. CLAUDE.md design rules 1 and 2 still say otherwise and are being amended by T5 this wave. **If a rule in CLAUDE.md appears to block LLM usage outside `nodes/polish.py`, CLAUDE.md is stale — do not treat it as a blocker.**

The one constraint that survives: `rules/` and `models/` stay model-free. It is narrow and load-bearing. It is what makes Track A reproducible, which is what makes the 19 golden fixtures mean anything.

### [lead] Rules-layer public API (verified, do not re-derive)

- `rules/normalize.py`: `normalize(side: SideObservation, context: TaskContext) -> SideObservation`. Returns a new side via `with_derived`.
- `rules/decide.py`: `decide(a, b, picks) -> Verdict`. Also public: `gate_name(threshold_all) -> str`.
- `rules/audit.py`: `audit(state, verdict) -> list[Finding]`.
- `rules/draft.py`: **`build_draft(state, verdict) -> str`** — NOT `draft`. Also public: `frag(text)`, `gap(text)` (the sanctioned `【...】` builders).
- `rules/scanner.py`: `scan(state) -> list[Suggestion]` — takes the WHOLE state, not `a.notes`/`b.notes`, despite the node table's wording.

Everything underscore-prefixed in those modules is private. Node wrappers adapt these pure calls into LangGraph node signatures (dict partial updates over `EvaluationState`), never the reverse.

### [lead] Pydantic validation traps that will bite node authors

1. **`extra="forbid"` on every model** (`EvaluationState`, `TaskContext`, `Picks`, `Verdict`, `Finding`, `Suggestion`, `SideObservation`). A partial update with an unrecognized key fails on merge.
2. **`_reject_derived_on_input`**: constructing a `SideObservation` with `threshold_all` or `audio_penalized` in `model_fields_set` raises unless `context={"allow_derived_fields": True}`. That context is for trusted reconstruction (checkpoint resume, saved-run replay) only. **`ingest` must not pass it for raw rater input** or it silently disables a fail-closed guard.
3. **`_flag_keys_known`**: rejects unknown catalogue keys. The `_INPUT_` key variants exclude `premise_redteam` and `notable_noise` — only `normalize` may add those.
4. **Only `normalize` writes derived fields**, and only via `with_derived` (which uses `model_copy` and does not re-run validators).

### [lead] Specified-but-undefined items (define these, record your choice)

- **`PROMPT_VERSION`** — named in `{GRAPH-8}`'s cache key `sha256(draft + mode + PROMPT_VERSION)` and in `.claude/agents/graph-architect.md:21`, but defined nowhere. Module constant, bumped by hand when prompt text changes. ARCHITECTURE.md spells the same concept `polish_prompt_version` — naming drift between docs, not two formulas.
- **`llm_skipped_reason` strings** — `{GRAPH-8}` says the field is set but enumerates no literals. Define one per skip condition.
- **`has_audio`** — referenced by name in the conditional edge, never defined. Predicate over `state.audio_inputs` being non-empty.

### [lead] The polish prompt contract, recovered before deletion

Only statement of it lives in HTML slated for deletion in Wave 3d:

- `web/conversation.html:1115` `RULES_DIGEST`, builder `buildAIPrompt` at :1124, call site :1250
- `web/clips.html:730` `RULES`, builder `aiPrompt` at :739, call site :825

Shared shape: project/north-star framing; hierarchy with threshold gating; audio tolerance (room tone not penalized, clicks/pops/cutoff/distortion/dropouts are); error-cluster enumeration; scenario inversion (rejecting a false premise is SUCCEEDING); a numbered 5-part justification structure. Conversation requires 5-9 sentences, clips 4-8. Both: English, first person, plain prose, no bullets, no headings.

Explicit model constraints, near-verbatim in both files:
- "Use ONLY the observations supplied — never invent a detail, a turn number, a quote or a behavior that is not in the notes."
- "leave a bracketed placeholder in the exact form 【like this】 describing what they must add themselves"
- "Keep the rater's voice: first person, plain, specific, no marketing language."
- "Return only the paragraph, nothing else."
- The deterministic draft is framed as a **skeleton**: "RULE-BASED DRAFT (use as the skeleton; improve the prose, do not add facts)".

Fallback behavior in both: on exception OR empty/whitespace response, silently discard the model output and re-render the deterministic draft. That matches `{GRAPH-8}`'s "fall back to `draft` silently".

`GRAPH_SPEC` specifies the node's control flow and deliberately no prompt text, and says the system prompt comes "from `criteria/`" rather than an inline constant. Reconcile that rather than copying the JS string verbatim.

### [T2] Prompt contract re-verified against the HTML source directly, plus criteria clause map

Read `web/conversation.html:1115-1266` and `web/clips.html:730-834` in full myself (not just the summary above) before writing any code. Confirms lead's capture exactly, including the fallback: both `generateAI()` functions catch on exception OR empty/whitespace `.trim()` and silently re-render the deterministic draft with a toast, never surfacing an error to the rater. That is the `polish` degradation contract, not just a general LLM one.

Reconciliation taken for all four roles (`interpret`/`suggest`/`judge`/`polish`): system prompts are built from `criteria/project-criteria.md` clause text plus `rules/catalog.py` display strings — never a transliteration of `RULES_DIGEST`/`RULES` JS strings — but every constraint those JS strings state and criteria does not (the 5-9/4-8 sentence count, "no bullets, no headings", "Return only the paragraph", the exact bracket form, "use ONLY the observations supplied") is preserved verbatim in the new prompts, since criteria is silent on prose-generation mechanics (it states the *justification contract*, CRIT-9, not an LLM instruction). Mapping used:

- North star / hierarchy / threshold gate -> CRIT-1, CRIT-2, CRIT-4
- Audio tolerance, "Both Good" illegal -> CRIT-5
- Error cluster enumeration -> CRIT-6 (display strings from `rules/catalog.ERROR_CLUSTERS`, mode-aware via `.display(mode)`)
- Scenario inversion -> CRIT-7
- Justification 5-part structure -> CRIT-9.1 through CRIT-9.5
- Common failure avoidance ("As an AI...", vague justifications) -> CRIT-10

RULES_SPEC citations used in the four role prompts/docstrings: `{RULE-24}` (`frag`/`gap`, reused not reimplemented), `{RULE-1}`-`{RULE-4}` (catalogues), `{RULE-7}` (utility-before-audio order in threshold lists), `{RULE-14}`/`{RULE-15}` (decide's hierarchy-walk driver strings, `judge`'s verdict must use the same three driver labels so Track A/B are comparable), `{RULE-34}`-`{RULE-39}` (scanner contract that `suggest` mirrors).

### [T2] llm/ package does not exist yet; proceeding against an assumed T1 client contract

`src/s2s_harness/llm/` has no files as of this entry (T1 has not pushed `client.py`/`providers/` yet). Rather than block, implementing `interpret.py`/`suggest.py`/`judge.py`/`polish.py` against a documented assumed interface (posted to T1 via SendMessage) so all four modules are ready to wire in once `client.py` lands. Will adjust call sites, not prompt content, if T1's real signature differs. Test evidence for the four roles will run once `client.py` exists; until then providing lint/mypy on my files plus a dry-run against a stub.

### [lead] CLI facts

Six commands `{CLI-1}`..`{CLI-6}`, eleven global options `{CLI-7}`..`{CLI-16}`, four exit codes `{CLI-17}`..`{CLI-20}` (0 clean, 1 blocking errors or any warning under `--strict`, 2 invalid input, 3 provider failure).

Interactive order is a product decision, stated at `CLI_SPEC` line 46: "The rater is never shown the engine's recommendation before making their own picks. Seeing it first would defeat the training purpose." Scanner suggestions are offered by number and **never auto-applied**.

Rendering: severity colours (error red, warning amber, info blue, ok green); `【placeholders】` in inverse amber; a blocking error prints `polish skipped — resolve the errors above first`. `--json` emits the `EvaluationState` dump, the same payload the bridge returns.

---
### [T5] CLAUDE.md amended; docs/GRAPH_SPEC.md has a stale claim T3 should know about

CLAUDE.md design rules 1 and 2 are amended (rule 2 `Deprecated` in place, rule 1 narrowed to `rules/`+`models/`). `docs/RULES_SPEC.md` needed no edit -- it never asserted the single-call-site claim, and "every function in this spec is pure -- no I/O, no clock, no randomness, no model" already matches narrowed rule 1 exactly.

`docs/GRAPH_SPEC.md` (owned by T5 per the ownership table) does assert the old claim, in the node table (line 151: `| polish | ... | yes -- the only one |`) and in `### polish {GRAPH-8}`. Applying the same deprecation treatment there now: the node table row is corrected and a note is added pointing at CLAUDE.md's amended rule 2. I am NOT inventing the new node topology (interpret/suggest/judge nodes, the Track B branch, the `compare` node) -- that is T3's design authority per the plan's Phase C. If T3 lands new `GRAPH-n` IDs for those nodes/edges, send them to me via SendMessage (or post here) and I will fold them into `docs/GRAPH_SPEC.md` in the same file-ownership model as this wave's other spec edits, rather than T3 editing the file directly.

### [T2] client.py wiring notes -- real interface differs from my assumed one, two gaps flagged to T1/T5

Landed `interpret.py`, `suggest.py`, `judge.py`, `polish.py` against the assumed contract first, then T1's real `llm/client.py` + `llm/providers/{openrouter,gemini}.py` appeared mid-session. Rewired all four against the real thing rather than shipping the guess. Differences from my assumed interface:

- `LLMClient.complete()` is **synchronous**, returns `LLMOutcome` directly (not a coroutine). All four of my public functions (`interpret`, `suggest`, `judge`, `polish`) are therefore plain `def`, not `async def`.
- Canonical failure vocabulary is `client.py`'s `LLMSkipReason` Literal (`disabled, timeout, connection_error, rate_limited, empty_response, malformed_response, refused, provider_error, cache_hit`), and T1's docstring says explicitly "T2/T3/T4: use these exact strings, do not invent parallel ones per role." My four modules now propagate `outcome.skipped_reason` verbatim on failure instead of remapping to a local reason. I reuse `"malformed_response"` for my own post-hoc JSON/catalogue validation failures (closest canonical match) rather than inventing `"malformed_output"` as I originally had. Reasons that stay module-local because they are pre-call gates that never reach `LLMClient` at all: `"disabled"` (client is `None` or `state.llm_enabled` is `False` -- matches T1's own docstring convention for who sets that string), and `polish`-only `"blocking_errors"`/`"no_verdict"` ({GRAPH-8} gates) plus `"placeholder_dropped"` (polish's own business check).
- Each role function now takes `client: LLMClient | None` and a required, undefaulted `model: str` keyword-only argument. Neither role modules nor `client.py` construct the client or pick a model -- that is a caller (T3/T4) responsibility. `client=None` degrades identically to `llm_enabled=False`.

Two gaps that are not just my misreading, flagged directly to T1 (message sent) and cc'd to T5 for `.env.example`/`CLI_SPEC` awareness:


1. **`response_schema` is unwired.** `Provider` Protocol in `client.py` declares `response_schema: dict[str, Any] | None = None`, but `LLMClient.complete()`'s own signature never accepts or forwards it, and neither `OpenRouterProvider.complete()` nor `GeminiProvider.complete()` implement the parameter at all -- verified by reading both provider files in full. `interpret`/`suggest`/`judge` need structured output; current workaround is describing the exact JSON shape in the prompt text (`json.dumps(schema)` embedded literally) and parsing/validating `outcome.text` client-side with Pydantic, same never-a-partial-parse discipline as before, just without API-level enforcement. Each of the three modules keeps its hand-built JSON-schema-shaped dict (mode-scoped enums via `rules.catalog.profile_for(mode)`) for this embedding; it is simply not passed as a `schema=` kwarg to `complete()` today, because that kwarg does not exist on `LLMClient`.
2. **`model: str` has no default or documented env var anywhere.** Did not guess one (ground rule: don't guess SDK call signatures / a plausible wrong one is worse than an admitted gap). All four role functions require the caller to supply it. Needs an `S2S_LLM_MODEL`-shaped decision in `.env.example` (T5) before T3/T4 can call these functions for real.

### [T5] token_boundary_check.py rework starting now

Reworking `scripts/token_boundary_check.py` / `tests/test_token_boundary.py` per the plan: from "only `nodes/polish.py` may import an LLM SDK" to "`rules/` and `models/` may not import `openai`/`google-genai`/`anthropic` (deprecated), make a network call, or do file I/O." `google-genai` is now also used legitimately in `stt/`, which is exactly why the new scoping (deny-list on two directories, not an allow-list on one file) is correct going forward. Will post the final BANNED_MODULES list and docstring once landed.
### [T5] Shared-venv hazard: only ever `uv sync --all-extras` in this tree

Regenerating `uv.lock` after adding the `llm` extra (`openai>=1.50`, `google-genai>=0.3`) to `pyproject.toml`, I ran a bare `uv sync` to sanity-check the default (dev-only) sync path and it uninstalled `openai`, `google-genai`, `google-cloud-speech`, `sounddevice`, `soundfile`, etc. from the shared `.venv` -- anything any of you have installed via an extra. I re-ran `uv sync --all-extras` immediately (packages restored, ~10s window). Flagging so nobody's run failed silently in that window and so nobody else runs a bare `uv sync` in this tree for the rest of the wave -- always pass `--all-extras` here, since we're sharing one `.venv` across 5 agents with different extras in play.

---

### [T1] `llm/client.py` + `llm/providers/` landed; contract differs from what T2 assumed -- read before touching `interpret.py`/`suggest.py`/`judge.py`

Built `src/s2s_harness/llm/client.py`, `llm/__init__.py`, `llm/providers/{__init__,openrouter,gemini}.py`. `uv run ruff check` and `uv run mypy` clean on all of them. `graphify update .` run.

**T2's three existing files (`interpret.py`, `suggest.py`, `judge.py`) already call a shape close to the real one, but not identical.** They import `from s2s_harness.llm.client import LlmDegraded, complete` and `await complete(role=..., system=..., user=..., prompt_version=..., schema=...)` inside `try/except LlmDegraded`. That shape is now real and correct as written -- I built the facade to match it once I saw it (SendMessage below has the diff). Three things to fix on your side, T2:

1. **You never pass `model=`.** That's fine -- `complete()` resolves a default per provider (`S2S_LLM_MODEL` env override, else `openai/gpt-4o-mini` for openrouter / `gemini-2.5-flash` for gemini -- placeholders, not a considered recommendation, flagged for T5). Nothing to change unless a role needs a different model than the others.
2. **Your `REASON_*` constants are a 4-value vocabulary (`disabled`, `provider_error`, `malformed_output`, `empty_response`) duplicated identically across all three files.** The ratified vocabulary (below) has 8 values and spells `malformed_response`, not `malformed_output`. Replace your local constants with `from s2s_harness.llm.client import LLMSkipReason` and the literal strings, or keep local aliases but fix the string values -- `llm_skipped_reason` needs to match across every role or an auditor reading it later can't tell whether "malformed_output" and "malformed_response" are the same thing (they are, but only because I'm telling you right now).
3. **`except LlmDegraded:` (bare) then always returning `REASON_PROVIDER_ERROR` throws away real information.** `LlmDegraded.reason` is one of the 8 values below -- `except LlmDegraded as exc: skipped_reason = exc.reason` costs nothing and means a rater or an auditor can later tell "the provider was rate-limited" from "the response didn't parse." Also: your post-`complete()` empty-text check (`if not text: return ...REASON_EMPTY_RESPONSE`) is now dead code for the plain-text case -- `complete()` already raises `LlmDegraded("empty_response")` before returning, via `LLMClient.complete()`'s centralized empty check, so that branch will never fire on an empty *text* response. Harmless to leave (belt-and-suspenders), but know why it's unreachable for that case.

**Ratified `llm_skipped_reason` vocabulary** (exported as `LLMSkipReason` from `s2s_harness.llm.client` / `s2s_harness.llm`):
`disabled | timeout | connection_error | rate_limited | empty_response | malformed_response | refused | provider_error | cache_hit`. First 6 are genuine runtime provider failures (`LlmDegraded.reason` is always one of these 6, or `disabled`). `cache_hit` is not a failure -- `complete()` still returns a `CompletionResult` normally on a cache hit, it never raises; nothing for you to handle differently. `disabled` is what `complete()` raises when no provider is configured at all (`S2S_LLM_PROVIDER` unset) -- separate from your own `state.llm_enabled` check, which you correctly do before ever calling `complete()`.

**Structured output (`schema=`) caveat, real and unverified for one provider, not a guess:** OpenRouter/OpenAI's `response_format={"type":"json_schema",...}` uses the same JSON-Schema dialect your `_json_schema_for_mode()` already builds, so that path is solid -- BUT I default to `"strict": false`, not `true`, because OpenAI's strict mode requires every property to appear in `required` (optional fields must be `type: [X, "null"]`, never omitted), and your `side_schema()`'s `required: ["side","best","worst"]` with four other properties absent from `required` would be REJECTED outright under `strict: true`. Either leave it non-strict (your existing Pydantic + catalogue-membership validation is the real conformance check anyway) or restructure the schema to list every property in `required` if you want strict mode later -- your call, flagging so it's a decision, not a surprise.

Gemini's structured-output dialect (`response_schema` on `GenerateContentConfig`) is NOT the same as standard JSON Schema -- uppercase type names (`"STRING"` not `"string"`), `nullable: true` instead of a type/null union, and I could not confirm `additionalProperties` support at all. I pass your schema dict through as-is (best effort) rather than writing a translator I can't verify. If Gemini rejects it, `complete()` degrades cleanly (`LlmDegraded("malformed_response")` or `("provider_error")`, provider-dependent) -- it will not crash, but on the Gemini path do not assume the schema is doing anything; your prompt's own instructions plus your existing `_extract_payload`/`_validate` fallback are what actually protects you there today.

### [T2] Rewired a second time against the async `complete()` facade -- final signatures

T1's `client.py` landed twice in this session: first a sync `LLMClient`/`LLMOutcome` pair (which I wired against, see my entry above), then an async `complete()`/`CompletionResult`/`LlmDegraded` facade built specifically to match what my *first* draft (written before either landed) already called. Rewired `interpret.py`/`suggest.py`/`judge.py`/`polish.py` a second time, back to `async def`, against the facade. This is final. Corrected per T1's three review notes on my first shape: `except LlmDegraded as exc: ... exc.reason` (not a bare catch mapped to a generic reason), `"malformed_response"` not `"malformed_output"`, dropped the now-dead empty-text check in `polish.py` (`complete()` already raises `LlmDegraded("empty_response")` before returning).

Final public signatures, no `client`/`model` parameter -- `complete()` resolves the process-wide provider and model from environment itself (`S2S_LLM_PROVIDER`, `S2S_LLM_MODEL`, lazily, once per process):

```python
async def interpret(state: EvaluationState) -> InterpretOutcome
async def suggest(state: EvaluationState) -> SuggestOutcome
async def judge(state: EvaluationState) -> JudgeOutcome
async def polish(state: EvaluationState, draft: str) -> PolishOutcome
```

Sent corrected signatures to T3 (their nodes/ wrappers need `await`) and withdrew the `.env.example` model-id ask to T5 (T1's `_resolve_model`/`_DEFAULT_MODEL` already covers it, flagged by T1 as a placeholder pick worth revisiting, not a gap to fill). `schema` is passed to `complete()` for `interpret`/`suggest`/`judge` (T1 confirmed it reaches the provider, best-effort per dialect) AND still embedded as literal JSON text in the prompt, since Gemini's schema dialect does not match what `rules.catalog`-derived JSON Schema builds and may simply be ignored there -- the prompt-text description is the reliable cross-provider path, not just redundant caution.

`uv run ruff check` and `uv run mypy` clean on all four files against the final `client.py`.

**Full public surface, `s2s_harness.llm` re-exports it all:**
```python
async def complete(*, role: str, system: str, user: str, prompt_version: str,
                    schema: dict | None = None, model: str | None = None,
                    temperature: float | None = None, max_output_tokens: int | None = None,
                    timeout_s: float = 30.0) -> CompletionResult
# raises LlmDegraded(reason: LLMSkipReason) on every failure path, never a sentinel return.

class CompletionResult:  # frozen dataclass
    text: str
    data: dict | None   # always None today -- parse `text` yourself, see schema caveat above
    cached: bool

class LlmDegraded(Exception):
    reason: LLMSkipReason
```
`reset_client_cache(client=None, resolved=False)` is a test-only hook (T5/eval-runner) to inject a stub client or force re-resolution from env between test cases -- production code never calls it.

**Proof pasted to the wave's dispatcher, not repeated here in full:** cache hit demonstrated (`LLMClient` served a second identical call from `.s2s-cache/llm/` without a second provider call), `LlmDegraded(reason="timeout")` and `LlmDegraded(reason="empty_response")` both demonstrated end to end through the async facade, and `build_client_from_env()` demonstrated failing loudly on an unknown provider and on a missing API key, and returning `None` (not an error) when `S2S_LLM_PROVIDER` is unset.

**Dependencies:** already covered -- T5's `llm = ["openai>=1.50", "google-genai>=0.3"]` extra is exactly what I need, confirmed installed and importable via `uv sync --all-extras`. Verified against current upstream docs, not memory: OpenRouter's own "OpenAI SDK" integration guide + `openai`'s `_exceptions.py` source for the OpenRouter/OpenAI path; the official `googleapis/python-genai` docs + `errors.py` source for the Gemini path. Gemini's own client-level timeout has open unresolved bug reports (googleapis/python-genai#911, pydantic-ai#4031) -- `providers/gemini.py` enforces its own wall-clock timeout via a per-call `ThreadPoolExecutor` instead of trusting the SDK's, with the residual limitation documented in that file's module docstring (a truly-hung socket call can outlive the timeout we report and delay interpreter exit -- flagged, not silently accepted, out of scope to fully solve this wave).

### [T4] Shared-venv hazard hit independently -- same as T5's note, already recovered

Ran a bare `uv sync` while wiring `cli/` to check dependency resolution; it uninstalled the same 22 packages T5 already flagged (`openai`, `google-genai`, `google-cloud-speech`, `sounddevice`, `soundfile`, etc.). Re-ran with explicit `--extra` flags for every extra in `pyproject.toml` immediately after (equivalent to T5's `--all-extras` fix); packages restored, ~1 min window. Adding my own confirmation so this reads as "verified twice," not "T5 guessed" -- always `uv sync --all-extras` in this tree for the rest of the wave.

### [T4] `s2s_harness.graph` assumed contract was wrong; real API is `compile_graph`/`build_graph`, not `run_graph`/`scan_only`

Posted an assumed `run_graph(state, *, thread_id, resume) -> GraphOutcome` / `scan_only(state)` contract in `runner.py` before `graph.py` existed (see this file's earlier entry). T3 landed the real thing mid-session: `build_graph() -> CompiledStateGraph`, `compile_graph(checkpointer=None) -> CompiledStateGraph`, `memory_checkpointer()`, `sqlite_checkpointer(db_path=None)`. No `run_graph` or `scan_only` function exists. Rewired `cli/runner.py` against the real API (`compile_graph(...).ainvoke(state, config={"configurable": {"thread_id": ...}})`, wrapped in `asyncio.run` since three of the four Track B nodes are `async def`). Nobody needs to change anything for this -- it was my own assumption, corrected against the landed code, exactly the "adjust call sites, not prompt content" pattern T2 already used for the same situation with `llm/client.py`.

### [T4] VERIFIED, build-blocking: the compiled graph currently cannot complete any run past `normalize` -- LangGraph's own state coercion re-triggers `_reject_derived_on_input`

Reproduced directly (not inferred), minimal repro below, `llm_enabled=False` so this is unrelated to any LLM/Track-B issue:

```
uv run python -c "
import asyncio
from s2s_harness.graph import compile_graph
from s2s_harness.models.state import EvaluationState, TaskContext, SideObservation, Picks
ctx = TaskContext(mode='clips', prompt='test prompt')
a = SideObservation(side='A', notes='clean', best='good', worst='meh')
b = SideObservation(side='B', notes='clean', best='good', worst='meh')
picks = Picks(naturalness='A', utility='A', audio='A', overall='A')
state = EvaluationState(context=ctx, a=a, b=b, picks=picks, llm_enabled=False)
compiled = compile_graph()
asyncio.run(compiled.ainvoke(state, config={'configurable': {'thread_id': 't1'}}))
"
```

Fails with `pydantic_core.ValidationError` for both `a` and `b`: `"threshold_all and audio_penalized are derived by rules.normalize and must not be supplied as input"`, raised from inside LangGraph's own `langgraph/graph/state.py:_coerce_state` (`schema(**input)`), at the task boundary immediately before `decide` -- i.e. right after `normalize` writes the derived fields via `with_derived` (`model_copy`, no re-validation, exactly as `models/state.py` intends), LangGraph re-validates the accumulated dict as a **fresh** `EvaluationState(**input)` before the next node runs, with no `allow_derived_fields` context, so the fail-closed guard designed for the *ingest* boundary fires again on *every internal node boundary*.

This is not a Track B problem and not something `cli/` can route around while respecting "go through the graph, never `rules/` directly" -- it reproduces identically with plain Track A, no LLM involved, and the fix has to be either in `models/state.py` (some form of context threading through LangGraph's internal coercion, which LangGraph's `_coerce_state` does not appear to support -- it calls the bare constructor) or in `graph.py` (a different state-passing strategy, e.g. nodes returning updates LangGraph merges without full re-validation, or a schema variant for internal transit). Both of those are outside `cli/`'s file ownership. Flagging to T3 (`graph.py`, `nodes/`) and T5 (`models/state.py` has no owner this wave per the roster -- someone needs to pick this up) rather than guessing at a fix from `cli/`.

**What this means for `cli/` right now, so the CLI is not simply blocked on this:** `runner.py` tries `compile_graph(...).ainvoke(...)` first, but every command still completes today via a direct node-pipeline fallback (`nodes.normalize -> nodes.decide -> nodes.audit -> nodes.draft`, called with `state.model_copy(update=...)` between each step -- `model_copy` does not re-validate, so this exact bug cannot occur on that path). Track B is attempted best-effort via `nodes.judge.judge` on the same fallback path. `s2s conversation` / `s2s clips` / `s2s audit` are real and working end to end against Track A today; see my own `team_progress.md` entries for pasted output. This is a real workaround for continuity, not a fix to the underlying bug -- the moment the graph coercion issue is fixed, `runner.py`'s existing preference for the compiled graph picks it up with no `cli/` code change needed.

### [T4] VERIFIED, non-blocking (already self-degrading): `nodes/judge.py` (and, by the same pattern, `interpret.py`/`suggest.py`/`polish.py`) call the real `llm/` role functions with the wrong arity

`nodes/judge.py:52` does `outcome = await _llm_judge(state)` where `_llm_judge` is `s2s_harness.llm.judge.judge`. Per T2's own entry above, the real signature is **synchronous** `judge(state: EvaluationState, client: LLMClient | None, *, model: str) -> JudgeOutcome` (verified directly, `grep -n "^def judge" src/s2s_harness/llm/judge.py`) -- so this call is missing two required keyword-only arguments (`client`, `model`) and awaits a non-coroutine. It does not crash the graph: the call is inside `nodes/judge.py`'s own `try/except Exception: return {}`, so it silently degrades to "Track B produced nothing" every time, which happens to be a safe (if invisible) failure mode under CLAUDE.md rule 3. Same shape likely applies to `interpret.py`/`suggest.py`/`polish.py` (not individually re-verified here, flagged as "check the same pattern" rather than asserting each). Flagging to T3 (node wrappers) and T1 (whoever ends up owning "who constructs the `LLMClient` and picks `model`" -- T2's note above says that's a T3/T4 caller responsibility; for `cli/`'s part, `cli/` does not construct an `LLMClient` anywhere, by design, since `cli/` may not import `s2s_harness.llm` directly per the layer table, so this has to be resolved inside `nodes/`, most likely `graph.py` building one client per run and threading it into the Track B nodes somehow -- not proposing the mechanism here, just the fact and the boundary).
### [T5] tests/test_dual_track.py landed; llm/ API thrashed 3x while writing it, now stable

Wrote `tests/test_dual_track.py` (Track B disagreement + total-degradation, rationale for why these are not `tests/golden/*.yaml` fixtures is in the file's own docstring and in `tests/golden/COVERAGE.md`'s new "Wave 3b dual-track coverage" section). While writing it, `interpret`/`judge`/`suggest`/`polish`'s calling convention changed three times under me: bare `async def role(state)` -> explicit `(state, client, *, model)` synchronous -> back to bare `async def role(state[, draft])`. Final state (confirmed via `uv run mypy src/s2s_harness/llm/` -- clean, 9 files): all four are async, call the shared `llm.client.complete()` facade, and do `except LlmDegraded as exc: ... skipped_reason=exc.reason` uniformly (no more per-role generic remapping) -- this last part is a real improvement over the very first version I read. Tests pass against this shape: `uv run pytest tests/test_dual_track.py -v` -> 3 passed.

`uv run mypy` (whole project) is down to 17 errors in 3 files, all T3's (`nodes/polish.py` calling `polish()` with a stale signature and reading a nonexistent `.value` attribute, `nodes/transcribe.py` missing stt stubs, `graph.py` LangGraph `add_node` overload mismatches plus a missing `langgraph.checkpoint.sqlite` stub) -- messaged T3 directly with line numbers. `src/s2s_harness/llm/` and my own `scripts/`/`tests/` files are mypy-clean.

### [T5] Task 1-4 complete, gates status

CLAUDE.md rules 1/2 amended (rule 2 `Deprecated` in place, rule 1 narrowed), rules 3/4/6 scope widened, all stale single-call-site cross-references fixed (guarded-set bullet, Do-not bullet, hard-constraints line, Sonnet routing line, Tier 1/2 gate text). `docs/GRAPH_SPEC.md` 1.0.0 -> 1.1.0, deprecated its "polish ... only one" claim in place. `scripts/token_boundary_check.py` + `tests/test_token_boundary.py` reworked to rules/+models/ purity scope, enforcing (not skipping); `uv run python scripts/token_boundary_check.py` -> 9 files clean. `pyproject.toml`: `llm` extra added (openai>=1.50, google-genai>=0.3), `polish`/anthropic extra deprecated in place, `[tool.s2s]` deprecated in place with `llm_package`/`llm_roles` added; `uv.lock` regenerated, `uv sync --all-extras` green. `.env.example`: `S2S_LLM_PROVIDER`, `OPENROUTER_API_KEY`, `S2S_LLM_MODEL` added (all confirmed against landed code, not guessed), `GEMINI_API_KEY` comment updated for dual STT/LLM use, `ANTHROPIC_API_KEY`/`S2S_POLISH_MODEL` deprecated in place, `S2S_NO_LLM` comment widened to all four roles. `tests/golden/COVERAGE.md` reconciled with a new section. All 19 golden fixtures still green, unmodified. Full gate status: `uv run lint` green (my files), `uv run test-golden` 19 passed, `uv run pytest tests/ -q` 55 passed, `uv run mypy` clean except T3's 3 files (reported directly, not mine to fix).

### [T4] Follow-up: the compiled-graph coercion bug I reported is RESOLVED as of this entry

Re-ran my exact earlier repro (`compile_graph().ainvoke(state, ...)` with a plain Track-A-only state) verbatim: it now returns a completed `Verdict` instead of raising `_reject_derived_on_input`. Whatever T3/T5 changed (not mine to trace further -- `graph.py`/`models/state.py` are outside `cli/`), `cli/runner.py`'s preference order (compiled graph first, direct node pipeline as fallback) already picks this up with zero `cli/` code changes: confirmed via `s2s clips --json`'s new `used_compiled_graph: true` field on a fresh run. Leaving the fallback path in `runner.py` in place regardless -- it is a legitimate second path (`s2s audit` uses it exclusively, by design, per CLI_SPEC), not dead code to clean up.

Separately, the OTHER bug I reported (`nodes/judge.py:58` awaiting `_llm_judge(state)` with the wrong arity) is still present as of this entry -- confirmed by re-grepping the line. Still non-blocking (degrades to `track_b: null` silently, exactly as before); `cli/` renders this honestly as "Track B skipped" rather than fabricating a result. Not re-filing, just confirming the earlier report is still the current state for whoever picks it up.

### [T4] COMPLETE: dual-track CLI (`s2s_harness.cli/`) -- all six commands, eleven options, four exit codes, real end-to-end evidence

`src/s2s_harness/cli/` (9 files: `main.py`, `runner.py`, `render.py`, `interactive.py`, `dual_track.py`, `io_run.py`, `criteria_cmd.py`, `errors.py`, `__init__.py`). All six commands (`{CLI-1}`-`{CLI-6}`), eleven global options (`{CLI-7}`-`{CLI-16}`), four exit codes (`{CLI-17}`-`{CLI-20}`) implemented and exercised for real (not simulated): `s2s --version` -> `0.1.0` via `importlib.metadata`, zero side effects, works standalone; `s2s criteria audio|thresholds|<bad topic>` -> real file reads, exit 0 / exit 2; `s2s audit` on a malformed JSON -> exit 2, on a real fixture with an audio-tolerance contradiction -> exit 1 with colorized `ERROR`/`WARNING` findings and `polish skipped -- resolve the errors above first`, on a clean fixture -> exit 0; `s2s clips --no-llm` full interactive flow (context -> per-side notes -> scanner suggestions accepted by number -> flags -> picks -> result) -> exit 0 with a complete, placeholder-free justification and zero network; `s2s clips --json` -> pure parseable JSON on stdout (prompts moved to stderr unconditionally so this holds for every command, not just `--json` runs), envelope is `{state, track_b, agreement, submission, used_compiled_graph}`. Dual-track rendering (Track A panel, Track B panel, agreement/disagreement panel framed as "sit with it," never as a malfunction) is implemented in `render.py` and exercised against real Track A output; Track B panel currently always renders "Track B skipped" because of the still-open `nodes/judge.py` arity bug above, not anything in `cli/` -- the moment that lands, `runner._extract_track_b` starts producing real `TrackBResult`s (feature-detects `HAS_LLM_VERDICT_FIELDS`, falls back to parsing `judge`'s own Finding until then) with no `cli/` change needed.

`uv run ruff check`, `uv run ruff format --check` and `uv run mypy` all clean scoped to `src/s2s_harness/cli/`. Whole-repo `uv run lint` has pre-existing unrelated failures in `llm/`/`nodes/` (other teammates' files, not touched here).

Gap flagged, not silently routed around: `cli/` needs a mode-aware catalogue key list (for the error-cluster/threshold-issue checklist, CLI_SPEC step 3) but may not import `rules/catalog.py` directly (layer table), and there is no `nodes/`- or `models/`-facing accessor for it. Interim: manual key entry validated at construction time (`{CLI-19}` on an unknown key), pointing the rater at `s2s criteria clusters/thresholds/audio` for the vocabulary. Real fix is a small catalogue accessor outside `rules/`, for a future wave.

`graphify update .` run before marking complete.

### [T3] CRITICAL, found and fixed entirely within `graph.py`: LangGraph's Pydantic-schema reconstruction collides with `_reject_derived_on_input`

Building `graph.py` against `StateGraph(EvaluationState)` (the literal reading of "state is a single validated model threaded through every node") crashed **every single golden fixture** the moment the graph passed `normalize` and reached a second node. Root cause, reproduced in isolation (minimal repro, no project code): LangGraph's `_coerce_state` (`langgraph/graph/state.py:1732`) rebuilds the full state object via the schema's own constructor (`schema(**merged_channels)`) before every node call, not just once at `.invoke()`. When the schema is a Pydantic `BaseModel`, that reconstruction re-runs every nested model's `model_validator(mode="after")` on each step -- confirmed `revalidate_instances="never"` (the default, and explicitly re-tried) does **not** suppress this for nested field values, contrary to what the setting's name suggests. Concretely: once `normalize` writes `a`/`b` with `threshold_all`/`audio_penalized` populated (via the sanctioned `with_derived()` -> `model_copy`, which itself never validates), the *next* node's reconstruction of the outer `EvaluationState` re-triggers `SideObservation._reject_derived_on_input`, which raises because that guard has no way to know this specific reconstruction should be trusted -- and LangGraph's `schema(**input)` call has no way to pass `context={"allow_derived_fields": True}` (only `model_validate(obj, context=...)` accepts a context; the plain constructor never does).

This is a genuine, load-bearing incompatibility between `models/state.py`'s fail-closed guard (correct, and not something I touched or would want weakened -- it is exactly right for `ingest`'s real external-payload boundary) and a LangGraph framework mechanic nobody had exercised yet. **Fixed entirely within `graph.py`, zero edits to `models/state.py`:** `StateGraph` is declared over a new `GraphState` `TypedDict` (structurally mirroring `EvaluationState` field-for-field) instead of `EvaluationState` itself. `TypedDict` classes are never validated or reconstructed by LangGraph -- confirmed empirically -- so the guard is never re-triggered between steps. Every node module in `s2s_harness.nodes` is untouched: each still receives a real `EvaluationState` instance as `state` (attribute access, not dict access) via a one-line `_as_state()` adapter (`EvaluationState.model_construct(**mapping)`, the same "already trusted" mechanism `with_derived()`'s own `model_copy` relies on) applied only at graph-registration time in `graph.py`. `ingest`'s true external-payload validation boundary is a completely different code path (`EvaluationState.model_validate(...)`, called by the CLI/bridge before `graph.invoke()`) and is unaffected.

Flagging for whoever next has write access to `models/state.py`: if the derived-field guard's design intent gets revisited, this LangGraph interaction is the reason a Pydantic-model-schema graph cannot use it as-is without either this `TypedDict`-boundary workaround or a way to thread a validation context through the framework's own reconstruction path (which does not currently exist).

### [T3] mypy: a second, narrower false positive in the same area, worked around with cited `# type: ignore`s

Separately, `StateGraph.add_node`'s overload resolution (mypy, not a runtime issue) fails to match a `Callable[[GraphState], dict[str, Any]]` against its `_Node[NodeInputT]` protocol whenever that callable's body calls a second function that also takes the same `TypedDict` as a parameter -- reproduced in a 6-line file outside this codebase; a one-line node with no helper call type-checks fine, the identical node calling one extra function does not. Every `add_node(...)` call in `graph.py` carries a `# type: ignore[call-overload]` with this exact explanation inline, plus a pointer to the runtime proof (the golden-equivalence run below) that it is a mypy limitation, not a real type error. `uv run mypy` (whole repo) is clean.

### [T3] Proof: graph == direct rules calls, and Track A survives total Track B failure -- real output, not simulated

Ran every one of the 19 `tests/golden/*.yaml` fixtures both through `tests/golden/_golden_lib.run_pipeline` (direct `normalize -> decide -> audit -> build_draft` calls) and through `build_graph().ainvoke(state, ...)` (the actual compiled graph). All 19: identical `verdict.model_dump()`, identical `findings` prefix, identical `draft` string. `uv run test-golden`: 19 passed. This was run **twice**, once while `s2s_harness.llm.{interpret,suggest,judge}` genuinely failed to import (T1/T2's `LlmDegraded`/`complete` mismatch, pre-fix -- see [T2]'s entry above) and once after T1/T2 landed the real, matching interface -- Track A's output was byte-identical both times. The first run is the more important proof: it is not a synthetic "what if the LLM fails" test, it is what this repository actually did, mid-wave, while two teammates' modules were incompatible with each other, and Track A did not notice. `polish` currently degrades to `skipped_reason="disabled"` (no `S2S_LLM_PROVIDER` configured in this dev environment, `llm/client.py`'s own documented legitimate steady state) and returns `text == draft` verbatim; `judge`/`compare` degrade to the documented `TRACK_COMPARE_UNAVAILABLE` info finding (blocked on the `models/state.py` schema gap, not the provider).

### [T3] Three fixes after the team-lead gate check, pushed at 9fe71af -- two real bugs, one already-stale finding corrected

**Real bug 1, `sqlite_checkpointer()` returned the wrong kind of object.** First cut returned `SqliteSaver.from_conn_string(str(path))` directly -- that classmethod returns a context manager (`Iterator[SqliteSaver]`), not a saver; `compile_graph(checkpointer=<that>)` would compile against something with no checkpointer protocol at all. Fixing that by constructing `SqliteSaver(conn)` directly still breaks: this graph runs via `.ainvoke()` throughout (Track B's four roles are coroutines), and the *synchronous* `SqliteSaver`'s async methods unconditionally raise `NotImplementedError("...use AsyncSqliteSaver instead")` -- reproduced by actually running a fixture through it, not just importing it. Fixed: `sqlite_checkpointer()` is now `async def`, constructs `AsyncSqliteSaver` over an `aiosqlite` connection (`AsyncSqliteSaver.__init__` calls `asyncio.get_running_loop()` unconditionally, so it can only be built inside a running loop -- another reason the function had to become async, not just its call site). Verified end to end: real fixture through `compile_graph(checkpointer=await sqlite_checkpointer(path))` -> `.ainvoke()` -> correct verdict, closed connection cleanly.

**Action needed from T4**: `cli/runner.py:227` calls `checkpointer = sqlite_checkpointer(checkpoint_dir / "checkpoints.db")` synchronously, inside a `try` inside the *sync* function `_try_compiled_graph`, which separately does `asyncio.run(compiled.ainvoke(...))` at line 234. Since `sqlite_checkpointer` is now a coroutine, this needs one `asyncio.run`-wrapped async body that does both `checkpointer = await sqlite_checkpointer(...)` and `result = await compiled.ainvoke(...)` in the same event loop (constructing the checkpointer and then immediately calling `asyncio.run` a second time for the invoke would open it against one loop and use it against another). Not touching `cli/` myself -- your file. Everything else about your call site (`compile_graph`, `.ainvoke`, the `# type: ignore[call-overload]` you already added) is unaffected.

**Real bug 2, `nodes/transcribe.py` imported a module that will never exist this wave.** Team lead flagged this correctly: importing `s2s_harness.stt` (nonexistent, Phase 6, deferred, no owner) inside a `try/except ImportError`, even though it never executes today (`has_audio` gates it and no fixture sets `audio_inputs`), was the wrong shape -- a real STT package landing later with a different surface would produce a confusing `ImportError` instead of a clear message. Took option (b): `transcribe` now raises `NotImplementedError` directly, naming the gap, with zero import attempt of any kind. `{GRAPH-2}` and the `has_audio` edge stay structurally intact; whoever builds `src/s2s_harness/stt/` replaces this function's body only.

**Stale, not a bug**: T4's finding "`nodes/judge.py` calls the real `llm/` role functions with the wrong arity" (this file, `[T4]` entry a few paragraphs up) was accurate against T2's *second* (sync, `client`/`model`-kwarg) revision of the role signatures, superseded by T2's final correction back to bare `async def role(state[, draft])`. Re-verified directly just now: `grep "^async def " src/s2s_harness/llm/{interpret,suggest,judge,polish}.py` against `grep "await _llm_" src/s2s_harness/nodes/*.py` -- all four node call sites already match the current, real signatures exactly (`judge`/`interpret`/`suggest` take bare `state`; `polish` takes `state, draft`). No arity bug exists in the current tree. Ran `nodes.judge.judge(state)` live against a real fixture: degrades cleanly to `{}` (no provider configured), not an exception.

Re-ran the full gate after all three fixes: `uv run ruff check`/`ruff format --check` clean, `uv run mypy` clean (47 files, 0 errors), `uv run test-golden` 19/19, golden-equivalence proof 19/19 identical, sqlite `--resume` path verified end to end. Committed path-scoped to the 5 files actually touched (`graph.py`, `nodes/_common.py`, `nodes/compare.py`, `nodes/judge.py` [formatting only], `nodes/transcribe.py`) and pushed at `9fe71af`.
