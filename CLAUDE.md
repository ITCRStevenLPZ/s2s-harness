# S2S Arena Harness — project guidance

A rating-assistant harness for the **Live S2S Arena / Stereo Headphone Check Project**. It merges two previously separate tools into one engine:

- **Conversation mode** — a rater holds a ≥4-turn voice conversation with Model A and Model B under identical conditions, then votes.
- **Clip mode** — a rater compares two single audio responses (Clip A / Clip B) to the same prompt, then votes.

Both modes share the same criteria, the same rules engine, and the same justification builder. Only the input schema and a handful of mode-specific validations differ.

The harness does **not** rate for the user. It ingests the rater's own observations, applies the project criteria deterministically, surfaces contradictions in their reasoning, and drafts the English justification they will edit and own.

Normative requirements live in `docs/RULES_SPEC.md` and the sibling specs. Project criteria live in `criteria/project-criteria.md`. Both outrank any assumption made in this file. If this file and a spec disagree, the spec wins and this file is the bug.

---

## Status

**This repository currently contains specifications only.** No implementation exists yet. `docs/BUILD_PLAN.md` is the ordered build sequence. Read the spec for a subsystem before writing any of its code.

`graphify-out/` does not exist yet either. See the bootstrap condition below.

---

## Non-negotiable design rules

These are architectural constraints, not preferences. Violating any of them is a build failure. Each rule names the mechanism that catches its violation. An unenforced rule is a suggestion, and suggestions decay across sessions.

**Amended 2026-07-27 (Wave 3b).** The owner rejected the original one-sanctioned-call-site architecture. LLM assistance and the deterministic rules engine now run as two balanced tracks over the same state — Track A (deterministic, always on) and Track B (LLM, four roles) — not one track with a single narrow LLM escape hatch. Rule 2 below is superseded and marked `Deprecated` in place rather than deleted, per this file's own deprecation rule. Rule 1 survives but is narrowed to name exactly the boundary that is still load-bearing. Rules 3, 4 and 6 are unchanged in substance but now bind a wider surface; each says so inline. If any other text in this file still reads as if only `polish` may call a model, that text is the bug, not this section.

1. **`src/s2s_harness/rules/` and `src/s2s_harness/models/` contain zero LLM calls, no network I/O, no clock, no randomness.** Every gate, threshold check, hierarchy walk and contradiction test is pure, deterministic Python. Same input to the same verdict, forever. If you find yourself reaching for a model to decide something inside those two packages, the rule is underspecified. Go fix `docs/RULES_SPEC.md` instead of papering over it with inference.
   This used to read simply "the rules engine contains zero LLM calls," which a future maintainer could over-generalize into "no LLM calls anywhere in the codebase." It was never that broad, and Wave 3b makes the narrower reading explicit: this is not a general restriction on LLM usage — `src/s2s_harness/llm/` and the four LLM roles exist deliberately, see rule 2. What survives is narrower and load-bearing: it is what makes Track A's verdict reproducible, which is what makes the 19 golden fixtures and the determinism suite (`tests/test_determinism.py`) mean anything. A verdict that can depend on a model call is not fixture-testable the same way, and the two-tier test gate below assumes Track A is not.
   *Enforced by:* `token-auditor`; `scripts/token_boundary_check.py` and `tests/test_token_boundary.py`, reworked in Wave 3b from "only `nodes/polish.py` may import an LLM SDK" to "`rules/` and `models/` may not" (weaker claim, still catches the failure that matters — someone silently making a verdict non-reproducible by fixing a rules bug with a model call); `tests/test_layering.py`'s cross-layer consistency tests, which continue to guard the same `rules/`/`models/` boundary from the other direction (the two packages may not import each other either).

2. **Deprecated — "exactly one sanctioned LLM call site: the `polish` node."** Superseded 2026-07-27 (Wave 3b). LLM code now lives in `src/s2s_harness/llm/` (`client.py`, `providers/`), and there are four sanctioned call sites, one per LLM role, each with its own contract:
   - `interpret` — reads free-form rater notes, proposes structured best/worst/candidate flags. Proposed, not written; shown to the rater the way `scan`'s suggestions are.
   - `suggest` — notes plus the catalogue, emits `Suggestion[]` in the same shape `scan` emits, merged and deduped with the regex results. Never auto-applied.
   - `judge` — reads the full state and criteria, produces its own verdict, reasoning and confidence, shown beside Track A's. Disagreement between the two is surfaced, not resolved for the rater.
   - `polish` — rewrites the already-complete deterministic draft into better prose. It is still the only one of the four that touches the draft's *text*.
   None of the four may add a fact, change Track A's verdict, or introduce an observation absent from the rater's notes. That constraint — not the call-site count — is what was actually protecting output quality, and it is restated per-role above and in rule 4 rather than lost.
   *Enforced by (was):* `token-auditor` grepping the tree for any LLM SDK import outside `nodes/polish.py`, plus a Tier 2 assertion of the polish invariant against a real model response.
   *Enforced by (now):* there is no longer a single-file import restriction to enforce — rule 1's boundary is the one `token-auditor` and `scripts/token_boundary_check.py` check going forward. The no-invented-facts / no-verdict-change / placeholder-preservation contract for all four roles is enforced per-role by each role's own fixture coverage (tracked in `tests/golden/COVERAGE.md`) and, for `polish` specifically, by the pre-existing Tier 2 real-model assertion.

3. **The deterministic draft (Track A) is always produced,** whether or not any LLM role runs. `--no-llm` must yield a complete, submittable-quality justification. The model is an enhancement, never a dependency. This was already true when only `polish` could touch the draft; it now applies to all four roles — `interpret` or `suggest` failing or being disabled must not block `scan`'s regex suggestions from working, and `judge` failing must not block Track A's verdict from rendering.
   *Enforced by:* every golden fixture runs twice in Tier 1, with and without `--no-llm`; a Wave 3b degradation fixture additionally covers every LLM call failing at once with Track A still producing a complete result (see `tests/golden/COVERAGE.md`).

4. **Never invent observations.** Where the rater has not supplied a needed detail, the deterministic builder and all four LLM roles emit a bracketed placeholder in the exact form `【what the rater must add】`. Rendering highlights these. A draft with placeholders is correct output, not a bug. This bound only `polish` before Wave 3b; it now binds `interpret`, `suggest` and `judge` too, since all three can surface text back to the rater.
   *Enforced by:* placeholder-format assertion in the golden suite; the CJK bracket pair is exact and is part of the guarded set.

5. **Criteria live in `criteria/`, not in code.** The rules engine reads its thresholds, cluster names and hierarchy from that directory. Changing project criteria means changing `criteria/project-criteria.md` and the constants derived from it, never hardcoding a new rule inline.
   *Enforced by:* `criteria-keeper` review plus a no-magic-literals check over `src/s2s_harness/rules/`.

6. **The rater's ears are the source of truth.** Speech-to-text transcribes *the rater's spoken notes*. It never listens to the model clips and never produces an audio-quality judgement. See `docs/STT_SPEC.md` for the one narrow, off-by-default exception and why it is advisory only. This now also binds `judge`: it reads the rater's notes and structured state, never audio. `docs/STT_SPEC.md` section 6 is unchanged by Wave 3b.
   *Enforced by:* the STT adapter interface accepts only a rater-notes channel; fixture coverage in both languages.

**Standing instruction:** when a rule appears to conflict with the task, stop and say so. Do not improvise a resolution. Underspecification is a spec bug. Fix `docs/`, then implement.

---

## The criteria, in one screen

Everything the engine does derives from these. Full text in `criteria/project-criteria.md`.

**Hierarchy:** `Naturalness / Engagement / Aesthetics > Utility > Audio Quality`

**Threshold gate (runs first).** Naturalness only carries its weight once both sides clear a minimum bar. Threshold breaches: hallucination, misinformation, accepting a false premise, major instruction-following failure, audio cutoff, clicks/pops, distortion, dropouts, notable distracting background noise. A side that breaches while the other is clean should not be preferred, unless the rater explicitly argues, with evidence, that the breach is minor and naturalness still wins.

**Audio tolerance.** Slight room tone or faint "air" is *not* penalized. `Both Good` on Audio Quality is illegal when either side has a noticeable artifact.

**Error clusters** (report, do not auto-disqualify): repetitive phrasing across turns; responses degrading as the conversation continues; the model interrupting the rater; the model ignoring the rater's interruptions or corrections; awkward silences; embodied-experience claims; speech-recognition failures; refusal to follow instructions.

**Scenario inversion.** In hallucination-fishing / false-premise scenarios, a model that rejects or corrects the false claim is **succeeding**. Never score correct pushback as a refusal.

**Justification contract.** Clear preference, then which hierarchy level decided it and why, then specific observable evidence from **both** sides, then an explicit threshold statement (observed or not observed, and whether audio was penalized), then every error cluster named. English, first person, plain prose.

---

## Pure Orchestrator Mandate (zero-write policy)

The root workspace session (`s2s-orchestrator`, pinned to **Opus or Fable only**) acts exclusively as a strict analytical coordinator, strategic planner, and post-flight evaluator.

* **Zero-write invariant:** the orchestrator must never write, mutate, or create source code, specs, criteria, or configuration directly, in any capacity, including when acting as an Agent Team lead. Known failure mode to guard against: a team lead starting to implement tasks itself instead of waiting for teammates. If this happens, stop and re-delegate. All changes route through Sonnet subagents or Sonnet agent teams.
* **Primary responsibilities:** state inspection, structural context parsing via `graphify`, deterministic triage of tool and skill pipelines, subagent or team dispatch, spec-traceability checks, and evidence-based post-flight validation.
* **Verification standard:** never accept "looks done" as a completion signal. Require the dispatched worker to return concrete evidence: `uv run mypy` output, golden-suite results, `graphify update` confirmation, or a diff. Anything else is an unverified claim.
* **Criteria review is read-only.** The orchestrator is the reviewer of record for any change under `criteria/`, and reviews without editing. Sonnet drafts, Opus approves or rejects with reasons, Sonnet revises.
* **Settings lock:** never modify `.claude/settings.json` or its hooks, plugin, or env configuration. That file is operator-managed. Treat it as read-only ground truth about what capabilities exist.

---

## Mandatory knowledge graph protocol (graphify)

The workspace uses an entity-relationship knowledge graph tracked at `graphify-out/` to bypass expensive recursive grep searches, reinforced by the `PreToolUse` hook in `.claude/settings.json` that injects a `graphify` reminder whenever a Bash `grep`/`rg`/`find`-style command is attempted.

* **Always enforced:** run `command -v graphify` at session start. If present, run `graphify query "<question>"` before any traditional codebase search or file inspection. This is a MUST, not a fallback.
* Use `graphify path "<A>" "<B>"` to trace dependencies across subsystems, and `graphify explain "<concept>"` to extract isolated architectural logic.
* Traverse components through `graphify-out/wiki/index.md` instead of brute-force navigation.
* Never parse raw graph artifacts (`graph.json`, `manifest.json`) directly. Read them entirely through CLI queries.
* **Bootstrap condition:** `graphify-out/` does not exist yet in this greenfield workspace. The first dispatched task (a single low-complexity Sonnet subagent) must run `graphify update .` before any other discovery work proceeds. Until that index exists, the hook will not fire and the mandate above is inert.
* **Spec-first caveat:** graphify indexes code, and this repo currently has none. Until implementation begins, `docs/` and `criteria/` remain the primary read path and graphify is for spec and fixture structure only.

### Graph freshness mandate (definition of done)

* Every Sonnet subagent or team member that completes an implementation task, change sequence, or refactor must run `graphify update .` before returning control or marking its task complete.
* The orchestrator verifies graph metadata currency during post-flight evaluation before declaring any task complete.

---

## Mandatory agent team communication protocol

Agent teams are enabled in this workspace (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` set in `.claude/settings.json`, `teammateMode: tmux`). Unlike subagents, which only report results back to the caller, teammates run as independent sessions that message each other directly and self-coordinate through a shared task list. Whenever the complexity score routes to a team this is a hard requirement: **do not simulate a team with sequential solo subagents.**

* **Formation:** scaffold shared state first via `/planning-with-teams:planning-with-teams`, then spawn the team with an explicit natural-language instruction that names each teammate, states its task boundary with the exact spec identifiers it must satisfy, and **explicitly specifies `Sonnet` as the model for every teammate**.
* **Team size:** 3 to 5 teammates per wave. If a change spans more than 5 subsystems, split into sequential waves rather than one oversized team.
* **File ownership:** assign each teammate a disjoint set of files and subsystems to prevent overwrite races. Cross-subsystem findings go directly to the affected teammate via `SendMessage`, never through the orchestrator as a relay.
* **Durable record:** persist a running record to `.claude/team-runs/<date>-<slug>/team_plan.md`, `team_findings.md`, and `team_progress.md`. These are what post-flight evaluation reads.
* **Plan-approval gate:** any team touching the guarded set below requires plan approval before implementation.
* **Reuse role definitions:** define each subsystem's worker once as a subagent definition under `.claude/agents/<subsystem>.md` with its model pinned in frontmatter.
* **Teammate shutdown discipline:** going idle is not the same as stopping. An idle teammate keeps its full context window alive.
  * **When it is safe to shut down:** all tasks marked `completed`, final findings sent, and no pending task names it as a dependency.
  * **How:** address the teammate by name and issue an explicit shutdown request.
  * **Sweep, do not wait:** after every task-list update, check for idle teammates and proactively request shutdown.
  * **Post-flight gate:** a wave is not complete until zero teammates remain idle-but-running. Record each shutdown request in `team_progress.md`.

---

## Deterministic effort calculation and delegation

The orchestrator computes an objective complexity score S:

```
S = (3 · R) + F + C
```

* **R** is the count of distinct subsystems affected by the scope, R ∈ {1..8} per the registry below.
* **F** is the estimated number of source files or fixtures requiring modification.
* **C** is the risk variance modifier. C = 5 if the change touches the guarded set, otherwise C = 0.

### Operational routing logic

* **S ≤ 5 (low complexity):** dispatch a single focused **Sonnet subagent** (via the Agent tool, `model: sonnet` passed explicitly) to handle linear changes without coordination overhead.
* **S > 5 (high complexity):** initialize a **Sonnet agent team** wave per the protocol above. Always required at this threshold, no exceptions for confidence.

Note that any guarded-set change carries C = 5 and therefore lands at S ≥ 8 even for a single-file edit. This is intentional. Criteria and invariant changes are never solo work.

---

## Model routing matrix

Model assignment is explicit and is not overridable via alias.

* **Opus or Fable (orchestrator only):** cross-stack judgment, criteria review, architectural contract layout, plan approval, final verdicts. Never writes, edits, or runs mutating Bash commands itself.
* **Sonnet (all implementation, exclusively):** rules engine, state schema, LangGraph nodes, STT adapters, CLI, bridge, web front ends, LLM role prompt authoring (`interpret`, `suggest`, `judge`, `polish` — widened from "polish prompt authoring" in Wave 3b, see design rule 2), fixture authoring, and all drafting of `criteria/` changes. Used both as solo subagents and as team members. Implementation workers must never be upgraded to Opus or Fable and must never fall back to Haiku.
* **Haiku (mechanical, non-authoring tasks only):** running the golden suite and reporting pass or fail, running the `token-auditor` grep, running `graphify update .`. A Haiku task that produces a source diff is a routing error. If a mechanical task turns out to require a judgement call, it escalates to Sonnet rather than guessing.

**Escalate on a predicate, not a feeling.** Work routes up a tier only when a checkable condition fires: the change touches `criteria/`; a golden fixture flips; a `Literal` gains or loses a member; the auditor grep fails; a threshold constant changes value. Anything that matches no predicate stays at its assigned tier.

---

## Operational plugin and skill triage matrix

Map tasks to the highest-efficiency path, using only capabilities actually enabled in `.claude/settings.json`. Verify availability before assuming.

| Target domain | Prescribed capability | Policy and scope constraint |
| --- | --- | --- |
| Codebase discovery | `graphify query`, `graphify path`, `graphify explain` | Primary query technique, mandatory before raw grep or find, enforced by the PreToolUse hook. |
| Multi-agent team formation | `/planning-with-teams:planning-with-teams` plus native Agent Teams (SendMessage, shared task list) | Mandatory for any S > 5 dispatch. Scaffolds the three team-run files before teammates are spawned. |
| Browser and interaction testing | `playwright` plugin | All front-end test automation against `web/` through the local bridge. Verifies the two HTML artifacts reject incomplete rater input and render `【placeholders】` as highlighted. |
| UI work on the rater-facing artifacts | `frontend-design` plugin | `web/` only. Styling changes never touch justification text content. |
| Sandbox and simulation | `superpowers` plugin | Validation phases that need an isolated run of the CLI or bridge without touching the real Anthropic or GCP endpoints. |

Deliberately absent: no vector store, no RAG layer, no database plugin. This harness has no retrieval component and adding one would breach design rule 1.

---

## Specs first and guarded subsystem contract

Before executing any modification plan, read the relevant spec under `docs/` and the governing section of `criteria/project-criteria.md`. Every dispatched task must cite the exact identifier or criteria clause it satisfies. Post-flight evaluation rejects work that cannot be traced to one.

**Identifier scheme.** Specs use stable prefixed IDs so that traceability is checkable rather than rhetorical: `RULE-n` (rules engine), `STATE-n` (schema), `GRAPH-n` (nodes and edges), `STT-n`, `CLI-n`, `BRIDGE-n`, `WEB-n`, `CRIT-n` (criteria clauses). A task that cannot name an ID is either out of scope or a missing spec, and both are the orchestrator's problem before they are a worker's.

**Guarded set (C = 5).** Any change to these requires a plan-approval-gated agent team regardless of file count:

* The hierarchy `Naturalness / Engagement / Aesthetics > Utility > Audio Quality` and the order in which it is walked.
* The threshold-breach list and the documented "rater argues the breach is minor" override.
* The audio tolerance rule, including the illegality of `Both Good` when either side has a noticeable artifact.
* The error cluster list and the report-but-do-not-disqualify semantics.
* The scenario inversion rule for hallucination-fishing and false-premise cases.
* Deprecated: "the single-call-site invariant." Superseded by design rule 1's `rules/`+`models/` purity boundary and design rule 2's per-role no-invented-facts / no-verdict-change / placeholder-preservation contract, both guarded here in its place — see the design rules section above for the full amendment.
* The `--no-llm` completeness guarantee.
* The exact placeholder token form `【...】`.
* Anything under `criteria/`, and any golden fixture under `tests/golden/`.

**Deprecation rule:** never delete a requirement entry from a spec. If a requirement becomes obsolete, mark it `Deprecated` in place and bump the document's Version header. The same applies to criteria clauses, which carry an audit trail back to the training material.

**Hard constraints, non-negotiable regardless of task:** no network calls, model calls, clock or randomness in `src/s2s_harness/rules/` or `src/s2s_harness/models/` (design rule 1; this replaces the pre-Wave-3b "no model call outside `polish.py`" phrasing, which is deprecated in place above); no bare dicts crossing a node boundary; Spanish and English coverage in every scanner pattern, phrase hint, and fixture.

---

## Two-tier test gate (mandatory)

`tests/golden/` encodes the four worked examples from the training material and is a hard merge gate to `main`. It is not advisory tooling. A failing or unrun tier blocks the merge regardless of how confident the change looks in isolation.

* **Both tiers required, every merge to main. No merge without BOTH green.**
  * `uv run test-golden` — Tier 1, fast, fully deterministic. Null STT provider, stubbed LLM roles, no network. Runs in seconds at zero API cost. Every fixture runs twice, once with `--no-llm` and once with the stub, and both must produce identical verdicts, identical hierarchy attribution, and identical placeholder sets. Covers every error-severity finding code and every threshold and hierarchy branch per `tests/golden/COVERAGE.md`; info and ok severity codes are out of scope, and `COVERAGE.md` is the authoritative record of what is covered and what is not.
  * `uv run test-golden-real` — Tier 2, the full path against the real provider (`S2S_LLM_PROVIDER=openrouter` or `gemini`, see `.env.example` — the `anthropic`/`ANTHROPIC_API_KEY` path is deprecated in place, superseded by these two per Wave 3b) and the real Gemini or GCP speech provider. Pre-merge gate only. Proves the integration works, not just the stubs, and asserts the polish invariant directly: the polished text introduces no observation absent from the deterministic draft, changes no verdict, and preserves every `【placeholder】` verbatim.
  * `uv run test-golden-all` runs both. Neither tier substitutes for the other.
* **A rate limit is not a defect:** Tier 2 failing with a genuine 429 or quota exhaustion from OpenRouter, Gemini, or GCP means "re-run when quota recovers." It is NOT a code defect and MUST NEVER be treated as a reason to skip the gate, merge anyway, or weaken the assertion to tolerate it. Tier 2 fails loudly by design. A run must never report green when it did not actually verify the integration.
* **Golden-flip rule:** if a change flips one of the four worked examples, the change is wrong until proven otherwise by a corresponding change in `criteria/`. A fixture edit with no criteria change to point at is rejected on sight.
* **Spec-sync mandate:** every new behavior and every fix must add or update fixtures in the same change. A feature without a fixture is INCOMPLETE, not "done pending tests." Do not report it complete.
* **Coverage-manifest mandate:** every new rule branch, error cluster, or front-end flow must be added to `tests/golden/COVERAGE.md` in the SAME change that introduces it, never a follow-up. `COVERAGE.md` reconciles fixtures against `criteria/project-criteria.md` clause by clause, which is what makes a coverage claim auditable instead of unverifiable. A matrix that silently drifts is worse than no matrix, because it looks true when it is not.

---

## Workspace layout and subsystem registry

Single repo. Each directory is owned by exactly one teammate or subagent role per wave. Cross-boundary changes go through the owning role, not around it.

| Directory | Subsystem | Spec refs |
| --- | --- | --- |
| `criteria/` | Project source of truth, rules and worked examples | `CRIT-*` |
| `src/s2s_harness/models/` | Pydantic state schema | `STATE-*` |
| `src/s2s_harness/rules/` | Deterministic engine, no LLM, no I/O | `RULE-*` |
| `src/s2s_harness/nodes/` | LangGraph node implementations | `GRAPH-*` |
| `src/s2s_harness/stt/` | Speech provider adapters (Gemini, GCP, null) | `STT-*` |
| `src/s2s_harness/cli/` | Typer entrypoint | `CLI-*` |
| `src/s2s_harness/bridge/` | FastAPI local endpoint for the HTML front ends | `BRIDGE-*` |
| `web/` | The two existing HTML artifacts, wired to the bridge | `WEB-*` |

Supporting, not counted in R: `docs/` (all specifications), `tests/golden/` (regression fixtures and `COVERAGE.md`), `.claude/agents/` (roster), `.claude/skills/` (runtime workflow skills), `.claude/team-runs/` (durable wave records), `graphify-out/` (knowledge graph).

### Graph conventions

* State is the only contract between nodes. A node reads state and returns a state delta, nothing else.
* Nodes are single-purpose and independently testable. If a node needs a comment explaining its second responsibility, it is two nodes.
* Edges and routing live in one file. Control flow is readable in one place, and no node decides where the graph goes next by side effect.
* Routing predicates are deterministic checks on typed state, never prose judgement handed to a model.
* Side effects live at the edges, in adapter and node code, never in the rules layer.

---

## Agent roster

Defined under `.claude/agents/`, one file per role, model pinned in frontmatter.

| Task | Agent | Model |
| --- | --- | --- |
| Drafting changes to criteria or the hierarchy | `criteria-keeper` | Sonnet, orchestrator reviews |
| Deterministic engine, gates, contradictions | `rules-engine-dev` | Sonnet |
| State schema, nodes, edges, checkpointing | `graph-architect` | Sonnet |
| Gemini and GCP speech adapters | `stt-engineer` | Sonnet |
| Terminal interface | `cli-dev` | Sonnet |
| Local endpoint plus HTML front ends | `bridge-dev` | Sonnet |
| Running the golden fixtures | `eval-runner` | Haiku |
| Checking no stray model calls crept in | `token-auditor` | Haiku |

A subagent returns a diff and a one-paragraph rationale, not a transcript. The orchestrator stays small on purpose. `token-auditor` runs last on every wave, and its failure blocks the change regardless of what the other roles reported.

---

## Working in this repo

* **Python 3.12+, `uv` for dependency management.** `uv sync`, then `uv run s2s`.
* **Type everything.** Pydantic models for state, `Literal` for enums, no bare dicts crossing a node boundary.
* **Tests before behavior changes.** See the golden-flip rule above.
* **Spanish and English inputs both matter.** The rater takes notes in either. Every scanner pattern, phrase hint, and test fixture must cover both.
* **Definition of done:** `uv run lint`, `uv run mypy`, `uv run test-golden-all` green; `graphify update .` run; `COVERAGE.md` reconciled; specs under `docs/` updated in the same change.

### Do not

* Add a model call to fix a case the rules engine gets wrong. Fix the rule.
* Widen a `Literal` to `str` to make a test pass.
* Add a dependency to the rules layer.
* Edit a golden fixture to match new behavior without a criteria change to point at.
* Let any LLM role (`interpret`, `suggest`, `judge`, `polish`) surface an observation the rater's notes did not already contain.
* Simulate an agent team with sequential solo subagents.
* Leave a teammate idle-but-running at the end of a wave.

Add a line here each time a rule gets violated in practice.

---

## Technical constraints

* Be thorough in reasoning, concise in output.
* Skip reading files over 100KB unless explicitly required.
* Do not use conversational openers or closing pleasantries.
* Do not use emojis or em-dashes in generated code, comments, specs, or justification text.
* Do not guess APIs, framework flags, dependencies, or commit records. Read codebase resources first to verify.
* Always keep `docs/` updated in the same change as the behavior it describes.