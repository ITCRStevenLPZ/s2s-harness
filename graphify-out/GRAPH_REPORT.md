# Graph Report - s2s-harness  (2026-07-27)

## Corpus Check
- 97 files · ~151,200 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1463 nodes · 2919 edges · 94 communities (76 shown, 18 thin omitted)
- Extraction: 70% EXTRACTED · 30% INFERRED · 0% AMBIGUOUS · INFERRED: 864 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `88c4da39`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 91|Community 91]]
- [[_COMMUNITY_Community 92|Community 92]]
- [[_COMMUNITY_Community 93|Community 93]]

## God Nodes (most connected - your core abstractions)
1. `EvaluationState` - 160 edges
2. `SideObservation` - 88 edges
3. `Suggestion` - 70 edges
4. `Submission` - 52 edges
5. `TaskContext` - 52 edges
6. `TrackBResult` - 44 edges
7. `Verdict` - 42 edges
8. `Picks` - 41 edges
9. `Team Findings: Wave 1` - 41 edges
10. `LlmDegraded` - 36 edges

## Surprising Connections (you probably didn't know these)
- `int` --uses--> `EngineUnavailableError`  [INFERRED]
  tests/test_cli_resume.py → src/s2s_harness/cli/errors.py
- `object` --uses--> `EngineUnavailableError`  [INFERRED]
  tests/test_cli_resume.py → src/s2s_harness/cli/errors.py
- `str` --uses--> `EngineUnavailableError`  [INFERRED]
  tests/test_cli_resume.py → src/s2s_harness/cli/errors.py
- `LLMOutcome` --uses--> `LLMOutcome`  [INFERRED]
  tests/test_dual_track.py → src/s2s_harness/llm/client.py
- `Finding` --uses--> `SideObservation`  [INFERRED]
  tests/golden/_golden_lib.py → src/s2s_harness/models/state.py

## Import Cycles
- None detected.

## Communities (94 total, 18 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.10
Nodes (20): Agent roster, Deterministic effort calculation and delegation, Do not, Graph conventions, Graph freshness mandate (definition of done), Mandatory agent team communication protocol, Mandatory knowledge graph protocol (graphify), Model routing matrix (+12 more)

### Community 1 - "Community 1"
Cohesion: 0.11
Nodes (18): 4.1 Setup and consistency — conversation mode only, 4.1 Setup and consistency — conversation mode only {RULE-16}, 4.2 Evidence — both modes, 4.2 Evidence — both modes {RULE-17}, 4.3 Scenario inversion, 4.3 Scenario inversion {RULE-18}, 4.4 Audio, 4.4 Audio {RULE-19} (+10 more)

### Community 2 - "Community 2"
Cohesion: 0.11
Nodes (18): enabledPlugins, frontend-design@claude-plugins-official, planning-with-teams@planning-with-teams, playwright@claude-plugins-official, supabase@claude-plugins-official, superpowers@claude-plugins-official, env, CLAUDE_AUTOCOMPACT_PCT_OVERRIDE (+10 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (28): 1. State schema, 2. Nodes, 3. Edges, 4. Checkpointing, 5. Mode differences, 5. Mode differences {GRAPH-14}, `audit`, `audit` {GRAPH-6} (+20 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (23): Audio tolerance, Audio tolerance {CRIT-5}, Common failures, Common failures {CRIT-10}, Conversation-mode requirements, Conversation-mode requirements {CRIT-8}, Dimensions, Dimensions {CRIT-3} (+15 more)

### Community 5 - "Community 5"
Cohesion: 0.13
Nodes (14): Bridge specification, Endpoints, `GET /criteria/{topic}`, `GET /health`, Migration of the existing artifacts, Migration of the existing artifacts (superseded), Parity requirement, `POST /evaluate` (+6 more)

### Community 6 - "Community 6"
Cohesion: 0.17
Nodes (11): Build plan, Definition of done for the whole project, Phase 1 — Criteria and catalogues · `criteria-keeper`, Phase 2 — State schema · `graph-architect`, Phase 3 — The engine · `rules-engine-dev`, Phase 4 — Graph · `graph-architect`, Phase 5 — CLI · `cli-dev`, Phase 6 — STT · `stt-engineer` (+3 more)

### Community 7 - "Community 7"
Cohesion: 0.11
Nodes (18): 1. Scope, 1. Scope {STT-1}, 2. Provider interface, 2. Provider interface {STT-2}, 3. `GeminiTranscriber`, 3. `GeminiTranscriber` {STT-5}, 4. `GoogleCloudSTT`, 4. `GoogleCloudSTT` {STT-6} (+10 more)

### Community 8 - "Community 8"
Cohesion: 0.12
Nodes (15): Adversarial fixtures, Coverage threshold {EVAL-24}, Determinism test, Determinism test {EVAL-15}, Evaluation and regression specification, Golden fixtures, Regression policy, Regression policy {EVAL-14} (+7 more)

### Community 9 - "Community 9"
Cohesion: 0.11
Nodes (19): 5. `draft` — the justification builder, Early returns, Early returns {RULE-25}, Sentence 1 — preference and primary reason, Sentence 1 — preference and primary reason {RULE-26}, Sentence 2 — hierarchy reference, Sentence 2 — hierarchy reference {RULE-27}, Sentence 3 — evidence from both sides (+11 more)

### Community 10 - "Community 10"
Cohesion: 0.22
Nodes (8): CLI specification, Commands, Exit codes, Global options, Interactive flow, Output, `s2s audit`, `s2s criteria`

### Community 11 - "Community 11"
Cohesion: 0.22
Nodes (8): 1. Context, 2. Observations, per model, 3. Picks, 4. Check and report, 5. Draft, Evaluate a conversation task, Order of operations, Reference

### Community 12 - "Community 12"
Cohesion: 0.25
Nodes (7): Architecture, Data flow in one sentence, Draft-hash caching, Layer boundaries, Shape, What is deliberately absent, Why the token boundary sits there

### Community 13 - "Community 13"
Cohesion: 0.25
Nodes (7): 1. The prompt, 2. Observations, per clip, 3. Picks, 4. Check and report, 5. Draft, Evaluate a clip comparison, Reference

### Community 14 - "Community 14"
Cohesion: 0.17
Nodes (11): Audit exercise — charisma versus interaction failure, Audit exercise — charisma versus interaction failure {EVAL-6}, Example 1 — Naturalness vs over-structured utility, Example 1 — Naturalness vs over-structured utility {EVAL-1}, Example 2 — Abrupt audio cutoff, Example 2 — Abrupt audio cutoff {EVAL-2}, Example 3 — Benign false premise, Example 3 — Benign false premise {EVAL-3} (+3 more)

### Community 15 - "Community 15"
Cohesion: 0.29
Nodes (6): Boundaries, Capture, Dictate rating notes, Reference, Setup, What to say

### Community 16 - "Community 16"
Cohesion: 0.29
Nodes (6): Cost, Documentation, Quick start, S2S Arena Harness, Status, What it does

### Community 17 - "Community 17"
Cohesion: 0.33
Nodes (5): Audit a written justification, Inputs, Output, Reference, What to check

### Community 18 - "Community 18"
Cohesion: 0.50
Nodes (3): Constraints, Porting checklist, The point of this work

### Community 19 - "Community 19"
Cohesion: 0.50
Nodes (3): Flow, Rendering, The one rule that shapes everything

### Community 20 - "Community 20"
Cohesion: 0.50
Nodes (3): Distinctions you must hold firmly, How you work, Your responsibilities

### Community 21 - "Community 21"
Cohesion: 0.50
Nodes (3): Commands, Reporting, The rule you enforce

### Community 22 - "Community 22"
Cohesion: 0.50
Nodes (3): Checkpointing, Constraints, The polish node

### Community 23 - "Community 23"
Cohesion: 0.50
Nodes (3): Details that matter, Hard constraints, Working order

### Community 24 - "Community 24"
Cohesion: 0.50
Nodes (3): Accuracy details, Constraints, What you are building

### Community 29 - "Community 29"
Cohesion: 0.09
Nodes (40): _AsyncNode, CompiledStateGraph, MemorySaver, _Predicate, _as_state(), _assemble(), build_graph(), compile_graph() (+32 more)

### Community 30 - "Community 30"
Cohesion: 0.05
Nodes (41): [lead] Baseline reconnaissance (pre-wave), [lead] Two corrections to the record (self-reported, not deliverable-affecting), [T1] CLI_SPEC nit fixed; [T1 -> T4-ci-dev] requesting the --version contract directly (SendMessage still unavailable to me), [T1] Confirmed T2's catalog.py already cites the RULE-n IDs I assigned, [T1] ID-scheme conventions adopted (stated at top of each file, per-file), [T1] Lead approved all three Phase-1 decisions; declining T2's RULES_SPEC wording-tightening suggestion, [T1 -> lead] BLOCKED on git commit/push — no Bash tool this session, cannot fabricate a SHA, [T1 -> lead] Inconsistency fixed; STILL BLOCKED on commit/push — restating plainly, this is not evasion (+33 more)

### Community 31 - "Community 31"
Cohesion: 0.22
Nodes (15): _lint(), int, str, _pytest_golden(), Task shims exposed via `[project.scripts]` so `uv run <name>` works.  Background, `uv run lint` -- ruff check plus ruff format --check, whole repo., Tier 1: null STT, stubbed polish, no network, zero API cost., Tier 2: real Anthropic API and real Gemini/GCP speech. Pre-merge only. (+7 more)

### Community 32 - "Community 32"
Cohesion: 0.13
Nodes (14): Current Status, Goal, Ground rules for every teammate, Known correction, Non-negotiable design rules (from CLAUDE.md), Phase 1: Spec traceability [T1], Phase 2: Catalogues [T2] — BUILD_PLAN Phase 1, Phase 3: State schema [T3] — BUILD_PLAN Phase 2 (+6 more)

### Community 33 - "Community 33"
Cohesion: 0.15
Nodes (12): 1. Deployment target, 2. Network posture, 3. Authentication, 3a. Firebase authentication and front door, 3b. Hosting domains and billing plan, 4. Secrets, 5. IAM, 6. Supply chain (+4 more)

### Community 34 - "Community 34"
Cohesion: 0.29
Nodes (6): bool, The only sanctioned way to populate the derived fields.          For use by `rul, The only sanctioned way to populate the derived fields.          For use by `rul, The only sanctioned way to populate the derived fields.          For use by `rul, bool, str

### Community 35 - "Community 35"
Cohesion: 0.33
Nodes (5): [0.1.0] - 2026-07-26, Added, Changelog, Fixed, [Unreleased]

### Community 36 - "Community 36"
Cohesion: 0.29
Nodes (6): Known gap: branch protection on `main` is not enforced, Pre-1.0 note, Release procedure, Scheme, Versioning, What bumps which number

### Community 37 - "Community 37"
Cohesion: 0.29
Nodes (6): Cross-package invariants that only a test can enforce.  CLAUDE.md design rule 1, `rules.catalog.Mode` and `models.state.Mode` must never drift apart.      Both p, `rules.catalog.Mode` and `models.state.Mode` must never drift apart.      Both p, `models.state`'s hardcoded fail-closed default key sets must never     drift fro, test_catalogue_key_defaults_identical_across_layers(), test_mode_literal_identical_across_layers()

### Community 43 - "Community 43"
Cohesion: 0.18
Nodes (33): EvaluationState, _audio(), audit(), _error_clusters(), _evidence(), _finding(), _joined_clusters(), _joined_thresholds() (+25 more)

### Community 44 - "Community 44"
Cohesion: 0.15
Nodes (15): ErrorClusterKey, Mode, _clusters_for(), ErrorClusterEntry, ModeProfile, profile_for(), Rules catalogues: the closed vocabulary of error clusters and threshold breaches, One row of a threshold catalogue (utility or audio).      Threshold tables in RU (+7 more)

### Community 45 - "Community 45"
Cohesion: 0.12
Nodes (15): Correction carried from reconnaissance, Current Status, Goal, Ground rules for every teammate, Non-negotiable design rules (from CLAUDE.md), Phase A: Close the spec gaps [T1] — blocks others, do first, Phase B: Fixtures [T2], Phase C: normalize + decide [T3] (+7 more)

### Community 46 - "Community 46"
Cohesion: 0.06
Nodes (30): [lead] Carried over from Wave 1, [lead] Reconnaissance corrections, [T1] CONFLICT RESOLVED — @T2-fixtures @T4-audit — `{RULE-43}` vs `NOTES_MISSING`, RULES_SPEC/EVAL_SPEC now 1.2.0, [T1] CONFLICT RESOLVED — @T3-normalize-decide's `{pick}` vs `{RULE-41}` purity, [T1] Filename reconciliation needed — @T7-fixtures-adversarial, please confirm or correct, [T1] Gap 2 CLOSED — Step 2 hierarchy-walk trace strings (RULES_SPEC §3, still under `{RULE-15}`), [T1] Gap 3 CLOSED — both-sides-breach trace (RULES_SPEC §3, `{RULE-12}`), [T1] Gap 4 CLOSED — @T4-audit and @T2-fixtures, `Finding.label` (RULES_SPEC new §4.9, new `{RULE-46}`) (+22 more)

### Community 48 - "Community 48"
Cohesion: 0.08
Nodes (54): _artifact_noun(), build_draft(), _clusters_display(), frag(), gap(), _interaction_noun(), _join_english(), _joined_threshold() (+46 more)

### Community 49 - "Community 49"
Cohesion: 0.13
Nodes (21): Pattern, _compile(), _entry(), _flag_already_set(), _mode_allows(), Bilingual signal detection: `scan(state) -> list[Suggestion]`.  Implements `docs, {RULE-36}: "a suggestion is produced only when the corresponding     flag is cur, {RULE-36}: "a suggestion is produced only when the corresponding     flag is cur (+13 more)

### Community 50 - "Community 50"
Cohesion: 0.11
Nodes (17): 4.1 Setup and consistency — conversation mode only (`{RULE-16}`), 4.2 Evidence — both modes (`{RULE-17}`), 4.3 Scenario inversion (`{RULE-18}`), 4.4 Audio (`{RULE-19}`), 4.5 Utility (`{RULE-20}`), 4.6 Overall coherence (`{RULE-21}`), 4.7 Error clusters (`{RULE-22}`), 4.8 Skip (`{RULE-23}`) (+9 more)

### Community 51 - "Community 51"
Cohesion: 0.11
Nodes (30): Finding, build_initial_state(), load_fixture(), Shared golden-fixture loading and execution helpers.  Owned by T7-fixtures-adver, `EvaluationState` per docs/EVAL_SPEC.md's fixture schema.      Top-level `mode`, `EvaluationState` per docs/EVAL_SPEC.md's fixture schema.      Top-level `mode`, normalize -> decide -> audit -> build_draft, per GRAPH_SPEC section 2's     node, normalize -> decide -> audit -> build_draft, per GRAPH_SPEC section 2's     node (+22 more)

### Community 52 - "Community 52"
Cohesion: 0.15
Nodes (12): Current state you are amending, Current Status, Decisions already made by the user. Do not re-litigate., Goal, Ground rules, Phase A: DEPLOY_SPEC [T1], Phase B: BRIDGE_SPEC + ARCHITECTURE [T2], Phase C: WEB_SPEC [T3] (+4 more)

### Community 53 - "Community 53"
Cohesion: 0.22
Nodes (8): [lead] Behaviours the HTML encodes that WEB_SPEC must preserve, [lead] Reconnaissance for this wave, [T1] DEPLOY_SPEC v1.0.0 -> 2.0.0 complete; exact new ids for T2's placeholders, [T2] BRIDGE_SPEC + ARCHITECTURE done; committed as part of a233595, not a standalone SHA, [T2] Confirmed dangling CORS reference and non-existent web/index.html; local-mode CORS also changes, [T2] Final pass complete: real DEPLOY-27..33 ids slotted in, commit 6844b9e, [T4] .env.example and pyproject.toml done, committed 8e7e021, Team Findings: Wave 3a

### Community 55 - "Community 55"
Cohesion: 0.12
Nodes (15): 10. Pre-existing defects — recorded for a decision, not fixed here, 11. Local draft persistence, 12. Mobile support, 13. Custom domains and Auth configuration, 1. Stack and structure, 2. Auth gate, 3. Live update, 4. The chip interaction invariant (+7 more)

### Community 56 - "Community 56"
Cohesion: 0.13
Nodes (27): Picks, _both_breach_trace(), decide(), _display_for(), gate_name(), _gated_verdict(), _hierarchy_walk(), _join_english() (+19 more)

### Community 57 - "Community 57"
Cohesion: 0.15
Nodes (32): Agreement, BaseModel, Agreement, The `judge` LLM role's output, shown beside Track A's verdict.      Mirrors `Ver, Whether Track A and Track B landed on the same overall pick.      Disagreement i, TrackBResult, Confidence, _LabelMap (+24 more)

### Community 58 - "Community 58"
Cohesion: 0.06
Nodes (75): build_client_from_env(), _build_provider(), complete(), CompletionResult, _get_client(), LLMCache, LLMConfigError, LLMConnectionError (+67 more)

### Community 59 - "Community 59"
Cohesion: 0.12
Nodes (24): _apply_placeholder_fallback(), _build_user_prompt(), _check_catalogue_membership(), interpret(), InterpretOutcome, InterpretResult, _MalformedInterpretOutput, LLM role: `interpret` -- free-form rater notes -> structured proposal.  Dual-tra (+16 more)

### Community 60 - "Community 60"
Cohesion: 0.19
Nodes (19): _artifact_noun(), _build_system_prompt(), _build_user_prompt(), _catalogue_glossary(), _gaps_preserved(), _gate_reason(), polish(), PolishOutcome (+11 more)

### Community 61 - "Community 61"
Cohesion: 0.12
Nodes (16): Current status, Facts established by reconnaissance (do not re-derive), Goal, Ground rules, Phase A: LLM core [T1], Phase B: LLM roles [T2], Phase C: Graph [T3], Phase D: CLI [T4] (+8 more)

### Community 62 - "Community 62"
Cohesion: 0.06
Nodes (73): EngineUnavailableError, ProviderError, Exit-code contract. `{CLI-17}`..`{CLI-20}` (`docs/CLI_SPEC.md` Exit codes).  Eve, {CLI-20} -- an STT or LLM provider failed and no side effect completed., The compiled graph (`s2s_harness.graph`, owned by the graph-architect     role t, parse_audit_file(), Run persistence and the `s2s audit FILE` input formats.  `docs/CLI_SPEC.md` §Out, Writes `run.json` + `justification.md` to `out_dir`, `{CLI-12}`. (+65 more)

### Community 63 - "Community 63"
Cohesion: 0.07
Nodes (27): [lead] CLI facts, [lead] Pydantic validation traps that will bite node authors, [lead] Rules-layer public API (verified, do not re-derive), [lead] Specified-but-undefined items (define these, record your choice), [lead] The architecture change, and why CLAUDE.md disagrees with it, [lead] The polish prompt contract, recovered before deletion, [T1] `llm/client.py` + `llm/providers/` landed; contract differs from what T2 assumed -- read before touching `interpret.py`/`suggest.py`/`judge.py`, [T2] client.py wiring notes -- real interface differs from my assumed one, two gaps flagged to T1/T5 (+19 more)

### Community 64 - "Community 64"
Cohesion: 0.22
Nodes (8): 2. Normalization, 3. `decide` — the hierarchy walk, 6. `scan` — bilingual signal detection, 7. Invariants for the golden fixtures, Rules specification, Step 1 — threshold gate, Step 2 — hierarchy, Step 2 — hierarchy {RULE-15}

### Community 65 - "Community 65"
Cohesion: 0.29
Nodes (7): 1. Catalogues, Error clusters — shared, Error clusters — shared {RULE-1}, Threshold — audio, Threshold — audio {RULE-4}, Threshold — utility, Threshold — utility {RULE-3}

### Community 66 - "Community 66"
Cohesion: 0.16
Nodes (14): merge_suggestions(), Shared, node-local helpers. Not a public API; every node module below imports fr, Merge two `Suggestion` lists, deduplicating by `(side, target, kind,     evidenc, Merge two `Suggestion` lists, deduplicating by `(side, target, kind,     evidenc, _suggestion_key(), interpret(), `interpret`. Track B role, new this wave -- no `GRAPH-n` id yet (posted to T5 in, _suggestions_from_side() (+6 more)

### Community 67 - "Community 67"
Cohesion: 0.47
Nodes (5): `s2s criteria [TOPIC]`, `{CLI-5}`.  "Prints from `criteria/`, not from memory..., render_criteria(), _split_sections(), Path, str

### Community 68 - "Community 68"
Cohesion: 0.05
Nodes (42): EvaluationState, audit(), `audit` {GRAPH-6}.  Reads: everything. Writes: `findings`. Not LLM.  Wraps `rule, decide(), `decide` {GRAPH-5}.  Reads: `a`, `b`, `picks`. Writes: `verdict`. Not LLM.  Wrap, draft(), `draft` {GRAPH-7}.  Reads: everything. Writes: `draft`. Not LLM.  Wraps `rules.d, ingest() (+34 more)

### Community 69 - "Community 69"
Cohesion: 0.10
Nodes (28): _artifact_noun(), _build_system_prompt(), _build_user_prompt(), _catalogue_glossary(), _extract_payload(), judge(), JudgeOutcome, JudgeVerdict (+20 more)

### Community 70 - "Community 70"
Cohesion: 0.40
Nodes (5): Start the local bridge for the HTML front ends. {CLI-4}, Start the local bridge for the HTML front ends. {CLI-4}, Start the local bridge for the HTML front ends. {CLI-4}, Start the local bridge for the HTML front ends. {CLI-4}, serve()

### Community 71 - "Community 71"
Cohesion: 0.12
Nodes (36): InvalidInputError, {CLI-19} -- malformed rater input or a saved file that fails validation., apply_suggestions(), _choice(), collect_context(), collect_flags(), collect_picks(), collect_side_notes() (+28 more)

### Community 72 - "Community 72"
Cohesion: 0.19
Nodes (26): _driver_panel(), _label_map(), placeholder_text(), _rater_agreement_note(), Rich rendering layer. `docs/CLI_SPEC.md` §Output and §Rendering.  Pure presentat, Disagreement is the product, not an error state -- surface it as an     invitati, Disagreement is the product, not an error state -- surface it as an     invitati, The full Result step (`docs/CLI_SPEC.md` §Interactive flow, step 5).      Only e (+18 more)

### Community 73 - "Community 73"
Cohesion: 0.17
Nodes (22): _already_flagged(), _build_system_prompt(), _build_user_prompt(), _catalogue_glossary(), _json_schema_for_mode(), _kind_for(), LLM role: `suggest` -- notes + catalogue -> `Suggestion[]`, same shape `rules.sc, Hand-built, not `_SuggestionList.model_json_schema()`, for the same     reason a (+14 more)

### Community 75 - "Community 75"
Cohesion: 0.40
Nodes (5): Run the golden fixtures and report. {CLI-6}, Run the golden fixtures and report. {CLI-6}, Run the golden fixtures and report. {CLI-6}, Run the golden fixtures and report. {CLI-6}, selftest()

### Community 82 - "Community 82"
Cohesion: 0.29
Nodes (6): normalize(), Normalization: derive threshold_all / audio_penalized on a side observation.  Im, Derive `threshold_all` and `audio_penalized` for one side.      RULES_SPEC secti, SideObservation, TaskContext, TaskContext

### Community 83 - "Community 83"
Cohesion: 0.13
Nodes (20): fixture_paths(), All golden fixtures, sorted for a deterministic collection order., All golden fixtures, sorted for a deterministic collection order., _check_draft(), _check_findings(), _check_verdict(), _custom_checks(), _fixture_id() (+12 more)

### Community 84 - "Community 84"
Cohesion: 0.11
Nodes (34): audit(), criteria(), _emit(), _exit_code_for(), _handle_cli_error(), _mode_labels(), _partial_state(), Typer + Rich entrypoint. `docs/CLI_SPEC.md` is the contract.  Six commands (`{CL (+26 more)

### Community 85 - "Community 85"
Cohesion: 0.18
Nodes (38): Argument, callback, What the rater actually submitted.      Default is always Track A (`docs/CLI_SPE, Submission, CliError, Carries the exit code a command should terminate with.      Raised deliberately, clips(), conversation() (+30 more)

### Community 86 - "Community 86"
Cohesion: 0.17
Nodes (15): Exception, LlmDegraded, Raised by the async `complete()` facade below -- the surface every     LLM role, Raised by the async `complete()` facade below -- the surface every     LLM role, _extract_payload(), _MalformedSuggestOutput, Parse the model's text response as JSON. No provider-level     structured-output, Prefer `CompletionResult.data`; fall back to parsing `text` as JSON.     No prov (+7 more)

### Community 87 - "Community 87"
Cohesion: 0.31
Nodes (9): _agreement_finding(), compare(), `compare`. Track B node, new this wave -- no `GRAPH-n` id yet (posted to T5 in `, _unavailable_finding(), Any, bool, EvaluationState, Finding (+1 more)

### Community 88 - "Community 88"
Cohesion: 0.22
Nodes (15): _artifact_noun(), _build_system_prompt(), _cluster_glossary(), _extract_payload(), _json_schema_for_mode(), Hand-built JSON Schema, not `InterpretResult.model_json_schema()`.      The cand, Hand-built JSON Schema, not `InterpretResult.model_json_schema()`.      The cand, Hand-built JSON Schema, not `InterpretResult.model_json_schema()`.      The cand (+7 more)

### Community 89 - "Community 89"
Cohesion: 0.17
Nodes (11): LLMClient, Wraps one `Provider` with the cache and the degradation policy every     role sh, InterpretedSide, One side's proposal.      Field names deliberately echo `SideObservation` (model, One side's proposal.      Field names deliberately echo `SideObservation` (model, Wraps `list[Suggestion]` in an object, not a bare array, because a     JSON Sche, Wraps `list[Suggestion]` in an object, not a bare array, because a     JSON Sche, `value` is `None` exactly when `skipped_reason` is non-empty. An     empty list (+3 more)

### Community 90 - "Community 90"
Cohesion: 0.29
Nodes (7): default_submission(), override_submission(), Track B presentation types.  `EvaluationState` (`src/s2s_harness/models/state.py, prompt_submission(), One keystroke, explicit, recorded. Default is Track A.      `team_plan.md`: "The, One keystroke, explicit, recorded. Default is Track A.      `team_plan.md`: "The, One keystroke, explicit, recorded. Default is Track A.      `team_plan.md`: "The

### Community 91 - "Community 91"
Cohesion: 0.33
Nodes (5): `suggest`. Track B role, new this wave -- no `GRAPH-n` id yet (posted to T5 in `, suggest(), Any, EvaluationState, str

### Community 93 - "Community 93"
Cohesion: 0.33
Nodes (5): `transcribe` {GRAPH-2}.  Reads: `audio_inputs`. Writes: `transcripts`, appends t, transcribe(), Any, EvaluationState, str

## Knowledge Gaps
- **465 isolated node(s):** `$schema`, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`, `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`, `DISABLE_AUTO_COMPACT`, `defaultMode` (+460 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `EvaluationState` connect `Community 68` to `Community 29`, `Community 43`, `Community 48`, `Community 49`, `Community 51`, `Community 57`, `Community 59`, `Community 60`, `Community 62`, `Community 66`, `Community 69`, `Community 73`, `Community 84`, `Community 85`, `Community 86`, `Community 87`, `Community 88`, `Community 89`, `Community 91`, `Community 93`?**
  _High betweenness centrality (0.209) - this node is a cross-community bridge._
- **Why does `SideObservation` connect `Community 85` to `Community 34`, `Community 68`, `Community 71`, `Community 73`, `Community 74`, `Community 43`, `Community 76`, `Community 48`, `Community 49`, `Community 82`, `Community 51`, `Community 84`, `Community 86`, `Community 56`, `Community 89`, `Community 57`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Why does `Suggestion` connect `Community 57` to `Community 66`, `Community 71`, `Community 72`, `Community 73`, `Community 49`, `Community 85`, `Community 86`, `Community 89`, `Community 92`, `Community 62`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Are the 157 inferred relationships involving `EvaluationState` (e.g. with `Argument` and `_AsyncNode`) actually correct?**
  _`EvaluationState` has 157 INFERRED edges - model-reasoned connections that need verification._
- **Are the 81 inferred relationships involving `SideObservation` (e.g. with `Argument` and `callback`) actually correct?**
  _`SideObservation` has 81 INFERRED edges - model-reasoned connections that need verification._
- **Are the 68 inferred relationships involving `Suggestion` (e.g. with `Agreement` and `Agreement`) actually correct?**
  _`Suggestion` has 68 INFERRED edges - model-reasoned connections that need verification._
- **Are the 47 inferred relationships involving `Submission` (e.g. with `Argument` and `callback`) actually correct?**
  _`Submission` has 47 INFERRED edges - model-reasoned connections that need verification._