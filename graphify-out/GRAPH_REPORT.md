# Graph Report - s2s-harness  (2026-07-26)

## Corpus Check
- 42 files · ~54,996 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 457 nodes · 442 edges · 43 communities (35 shown, 8 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d69d104c`
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

## God Nodes (most connected - your core abstractions)
1. `Team Findings: Wave 1` - 35 edges
2. `Project criteria — source of truth` - 23 edges
3. `2. Nodes` - 19 edges
4. `5. `draft` — the justification builder` - 19 edges
5. `Speech-to-text specification` - 18 edges
6. `4. `audit` — findings` - 17 edges
7. `S2S Arena Harness — project guidance` - 16 edges
8. `Evaluation and regression specification` - 12 edges
9. `Worked examples` - 11 edges
10. `Build plan` - 11 edges

## Surprising Connections (you probably didn't know these)
- `ErrorClusterEntry` --inherits--> `BaseModel`  [EXTRACTED]
  src/s2s_harness/rules/catalog.py →   _Bridges community 29 → community 34_

## Import Cycles
- None detected.

## Communities (43 total, 8 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.10
Nodes (20): Agent roster, Deterministic effort calculation and delegation, Do not, Graph conventions, Graph freshness mandate (definition of done), Mandatory agent team communication protocol, Mandatory knowledge graph protocol (graphify), Model routing matrix (+12 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (32): 1. Catalogues, 2. Normalization, 3. `decide` — the hierarchy walk, 4.1 Setup and consistency — conversation mode only, 4.1 Setup and consistency — conversation mode only {RULE-16}, 4.2 Evidence — both modes, 4.2 Evidence — both modes {RULE-17}, 4.3 Scenario inversion (+24 more)

### Community 2 - "Community 2"
Cohesion: 0.12
Nodes (16): enabledPlugins, frontend-design@claude-plugins-official, planning-with-teams@planning-with-teams, playwright@claude-plugins-official, supabase@claude-plugins-official, superpowers@claude-plugins-official, env, CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS (+8 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (26): 1. State schema, 2. Nodes, 3. Edges, 4. Checkpointing, 5. Mode differences, 5. Mode differences {GRAPH-14}, `audit`, `audit` {GRAPH-6} (+18 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (23): Audio tolerance, Audio tolerance {CRIT-5}, Common failures, Common failures {CRIT-10}, Conversation-mode requirements, Conversation-mode requirements {CRIT-8}, Dimensions, Dimensions {CRIT-3} (+15 more)

### Community 5 - "Community 5"
Cohesion: 0.15
Nodes (12): Bridge specification, Endpoints, `GET /criteria/{topic}`, `GET /health`, Migration of the existing artifacts, Parity requirement, `POST /evaluate`, `POST /polish` (+4 more)

### Community 6 - "Community 6"
Cohesion: 0.17
Nodes (11): Build plan, Definition of done for the whole project, Phase 1 — Criteria and catalogues · `criteria-keeper`, Phase 2 — State schema · `graph-architect`, Phase 3 — The engine · `rules-engine-dev`, Phase 4 — Graph · `graph-architect`, Phase 5 — CLI · `cli-dev`, Phase 6 — STT · `stt-engineer` (+3 more)

### Community 7 - "Community 7"
Cohesion: 0.11
Nodes (18): 1. Scope, 1. Scope {STT-1}, 2. Provider interface, 2. Provider interface {STT-2}, 3. `GeminiTranscriber`, 3. `GeminiTranscriber` {STT-5}, 4. `GoogleCloudSTT`, 4. `GoogleCloudSTT` {STT-6} (+10 more)

### Community 8 - "Community 8"
Cohesion: 0.13
Nodes (14): Adversarial fixtures, Determinism test, Determinism test {EVAL-15}, Evaluation and regression specification, Golden fixtures, Regression policy, Regression policy {EVAL-14}, Required fixtures (+6 more)

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
Cohesion: 0.08
Nodes (27): BaseModel, bool, EvaluationState, Finding, Picks, Preflight, Pydantic state schema for the S2S Arena harness.  Transcribed field-for-field fr, One recognized word with optional timing. STT_SPEC section 2. (+19 more)

### Community 30 - "Community 30"
Cohesion: 0.06
Nodes (35): [lead] Baseline reconnaissance (pre-wave), [T1] CLI_SPEC nit fixed; [T1 -> T4-ci-dev] requesting the --version contract directly (SendMessage still unavailable to me), [T1] Confirmed T2's catalog.py already cites the RULE-n IDs I assigned, [T1] ID-scheme conventions adopted (stated at top of each file, per-file), [T1] Lead approved all three Phase-1 decisions; declining T2's RULES_SPEC wording-tightening suggestion, [T1] No Bash tool in this session — cannot run `graphify update .`, [T1] Phase 1 complete — diff summary and rationale, awaiting lead review, [T1] Phase 1 fully closed — CLI-16 filled, final report to lead (+27 more)

### Community 31 - "Community 31"
Cohesion: 0.22
Nodes (15): _lint(), int, str, _pytest_golden(), Task shims exposed via `[project.scripts]` so `uv run <name>` works.  Background, `uv run lint` -- ruff check plus ruff format --check, whole repo., Tier 1: null STT, stubbed polish, no network, zero API cost., Tier 2: real Anthropic API and real Gemini/GCP speech. Pre-merge only. (+7 more)

### Community 32 - "Community 32"
Cohesion: 0.13
Nodes (14): Current Status, Goal, Ground rules for every teammate, Known correction, Non-negotiable design rules (from CLAUDE.md), Phase 1: Spec traceability [T1], Phase 2: Catalogues [T2] — BUILD_PLAN Phase 1, Phase 3: State schema [T3] — BUILD_PLAN Phase 2 (+6 more)

### Community 33 - "Community 33"
Cohesion: 0.18
Nodes (10): 1. Deployment target, 2. Network posture, 3. Authentication, 4. Secrets, 5. IAM, 6. Supply chain, 7. Privacy, 8. What is still deliberately absent (+2 more)

### Community 34 - "Community 34"
Cohesion: 0.15
Nodes (14): ErrorClusterKey, Mode, _clusters_for(), ErrorClusterEntry, ModeProfile, profile_for(), Rules catalogues: the closed vocabulary of error clusters and threshold breaches, One row of a threshold catalogue (utility or audio).      Threshold tables in RU (+6 more)

### Community 35 - "Community 35"
Cohesion: 0.33
Nodes (5): [0.1.0] - 2026-07-26, Added, Changelog, Fixed, [Unreleased]

### Community 36 - "Community 36"
Cohesion: 0.33
Nodes (5): Pre-1.0 note, Release procedure, Scheme, Versioning, What bumps which number

### Community 37 - "Community 37"
Cohesion: 0.29
Nodes (6): Cross-package invariants that only a test can enforce.  CLAUDE.md design rule 1, `rules.catalog.Mode` and `models.state.Mode` must never drift apart.      Both p, `rules.catalog.Mode` and `models.state.Mode` must never drift apart.      Both p, `models.state`'s hardcoded fail-closed default key sets must never     drift fro, test_catalogue_key_defaults_identical_across_layers(), test_mode_literal_identical_across_layers()

## Knowledge Gaps
- **308 isolated node(s):** `$schema`, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`, `defaultMode`, `PreToolUse`, `superpowers@claude-plugins-official` (+303 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Rules specification` connect `Community 1` to `Community 9`?**
  _High betweenness centrality (0.009) - this node is a cross-community bridge._
- **Why does `5. `draft` — the justification builder` connect `Community 9` to `Community 1`?**
  _High betweenness centrality (0.007) - this node is a cross-community bridge._
- **What connects `$schema`, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`, `defaultMode` to the rest of the system?**
  _340 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.09523809523809523 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.06060606060606061 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.11764705882352941 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.07407407407407407 - nodes in this community are weakly interconnected._