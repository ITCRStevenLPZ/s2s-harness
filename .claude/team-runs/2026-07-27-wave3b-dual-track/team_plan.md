# Team Plan: Wave 3b — Dual-track engine (deterministic + LLM in harmony)

## Goal

Build BUILD_PLAN Phase 4 (graph, nodes, checkpointing) and Phase 5 (Typer CLI) on a **dual-track** architecture, and amend the governance documents that currently forbid it.

## THE ARCHITECTURE CHANGE — read this before anything else

The repo's CLAUDE.md says the LLM may be called from exactly one file (`nodes/polish.py`) and nowhere else. **The owner has rejected that scoping.** LLM assistance and deterministic rules are to work as balanced tracks.

**When CLAUDE.md's design rules 1 and 2 appear to forbid LLM usage outside polish, CLAUDE.md is the stale document.** Do not quote it back as a blocker. It is being amended in this wave, by T5, in the same change as the code.

Two tracks run over the same `EvaluationState`:

| | Track A - deterministic | Track B - LLM |
|---|---|---|
| Runs | always, free, offline, no network | when enabled |
| Produces | verdict, findings, draft | observations, suggestions, its own verdict + reasoning, polished prose |
| Property | reproducible, auditable, fixture-gated | flexible, reads notes far better than regex |

**Disagreement between tracks is the product, not a bug.** Surface it. `criteria/project-criteria.md` frames the training value as the gap between the rater's instinct and the rules; a dissenting third opinion makes that gap visible.

**The rater submits.** Default is Track A's verdict. Overriding with Track B's is explicit, one keystroke, and recorded. Nothing auto-applies.

### The four LLM roles

| Role | Input | Output |
|---|---|---|
| `interpret` | free-form ES/EN notes | structured best/worst/candidate flags, proposed not written |
| `suggest` | notes + catalogue | `Suggestion[]`, same shape `scan` emits, merged and deduped with regex results |
| `judge` | full state + criteria | verdict + reasoning + confidence, shown beside Track A |
| `polish` | deterministic draft + observations | one paragraph, silent fallback to `draft` |

`scan`'s bilingual regexes STAY. They are free, instant and deterministic. The LLM adds recall on top; it does not replace them.

## The ONE constraint still being defended

**`src/s2s_harness/rules/` and `src/s2s_harness/models/` stay model-free.** No LLM SDK import, no network, no I/O, no clock, no randomness.

This is not a general restriction on LLM usage. It is narrower and load-bearing: it is what makes Track A reproducible, which is what makes the 19 golden fixtures and the determinism suite mean anything. Everything outside those two directories is open.

`scripts/token_boundary_check.py` is reworked from "one file may import an LLM SDK" to "`rules/` and `models/` may not". Weaker claim, truer one, still catches the failure that matters: someone fixing a rules bug by asking a model.

## Ground rules

1. **Read this file before major decisions.** Re-read it if you find yourself about to cite CLAUDE.md as a blocker.
2. **Cite an id in every deliverable**: `{GRAPH-n}`, `{CLI-n}`, `{RULE-n}`, `{STATE-n}`, `{EVAL-n}`, `{STT-n}`. No id for what you are building means a spec gap: report it, do not invent behavior.
3. **Stay inside your file ownership.** Cross-boundary needs go to the owner via SendMessage; if SendMessage is unavailable in your toolset (it has been for several agents in past waves), broadcast in `team_findings.md` and say so.
4. **Write findings immediately**, after at most 2 read/search ops. Do not batch.
5. **Final action: append `- [T-n] COMPLETE: <summary>` to `team_progress.md`.** In earlier waves silence was indistinguishable from success and cost real time.
6. **`git status` before every `git add`.** Path-scope every commit. Never `git add -A` or a bare directory — four other agents are live in this tree. A past wave had one agent's commit swallow another's half-finished work.
7. **Do not guess SDK call signatures.** Verify OpenRouter and `google-genai` against current documentation. A plausible wrong signature is worse than an admitted gap.
8. `graphify update .` before marking complete. No emojis, no em-dashes. Spanish and English in every new fixture.

## Providers

`S2S_LLM_PROVIDER` selects `openrouter` | `gemini`.
- **OpenRouter** via the OpenAI SDK with `base_url` pointed at OpenRouter.
- **Gemini AI Studio** via `google-genai`.
- `ANTHROPIC_API_KEY` and the `anthropic` extra are deprecated in place, never deleted.

## Team and ownership (disjoint)

| Teammate | Owns |
|---|---|
| T1 `llm-core` | `src/s2s_harness/llm/client.py`, `src/s2s_harness/llm/providers/` |
| T2 `llm-roles` | `src/s2s_harness/llm/{interpret,suggest,judge,polish}.py` |
| T3 `graph` | `src/s2s_harness/nodes/`, `src/s2s_harness/graph.py` |
| T4 `cli` | `src/s2s_harness/cli/` |
| T5 `governance` | `CLAUDE.md`, `docs/RULES_SPEC.md`, `docs/GRAPH_SPEC.md`, `scripts/token_boundary_check.py`, `.env.example`, `pyproject.toml`, `tests/` |

Do not touch `criteria/`, `src/s2s_harness/rules/`, `src/s2s_harness/models/`, `.claude/settings.json`, or `deploy/`.

## Facts established by reconnaissance (do not re-derive)

- **Public rules API**: `normalize(side, context)`, `decide(a, b, picks)`, `audit(state, verdict)`, **`build_draft(state, verdict)`** (note: NOT `draft`), `scan(state)` (takes the whole state, not just notes). Everything underscore-prefixed is private.
- **Validation traps**: every model is `extra="forbid"`, so a partial update with a stray key fails Pydantic on merge. Only `normalize` may write derived fields, and only through `with_derived`. `_reject_derived_on_input` and `_flag_keys_known` fail closed - `ingest` must NOT pass `allow_derived_fields` for raw rater input or it silently disables the guard.
- **Topology** {GRAPH-10} is specified in `docs/GRAPH_SPEC.md` section 3. `has_audio` and `should_polish` are pure predicates; `should_polish` re-evaluates the skip conditions because the edge is decided before the node runs.
- **Checkpointing** {GRAPH-12}: `MemorySaver` for a single run, `SqliteSaver` at `.s2s-cache/checkpoints.db` behind `--resume`, thread id = run id.
- **`PROMPT_VERSION`** is not defined anywhere yet. It is a module constant, bumped by hand when prompt text changes, and part of the cache key.
- **`llm_skipped_reason` strings are not specified** anywhere. Define them, record them in findings.
- **The polish prompt exists ONLY in the HTML that Wave 3d deletes**: `web/conversation.html:1115` (`RULES_DIGEST`), `web/clips.html:730` (`RULES`). Hierarchy, audio tolerance, cluster list, scenario inversion, 5-part structure, sentence counts (5-9 conversation / 4-8 clips), first person, no bullets, "use ONLY the observations supplied", "leave a bracketed placeholder in the exact form 【like this】", "Return only the paragraph". This is prior art for all four roles, not just polish. Recover it before it is lost.
- `tests/test_token_boundary.py` currently SKIPS because `nodes/polish.py` does not exist. It starts enforcing this wave.

## Phases

### Phase A: LLM core [T1]
- [ ] Provider protocol; OpenRouter (OpenAI SDK + base_url) and Gemini (`google-genai`) implementations
- [ ] Content-addressed cache in `.s2s-cache/`, key `sha256(input + role + PROMPT_VERSION)`
- [ ] Timeout, retry, silent degradation - every role falls back to its Track A equivalent, the tool never blocks on a provider

### Phase B: LLM roles [T2]
- [ ] `interpret`, `suggest`, `judge`, `polish`, each with its own prompt and `PROMPT_VERSION`
- [ ] All four preserve `【...】` verbatim and invent nothing
- [ ] Polish prompt contract recovered from the HTML

### Phase C: Graph [T3]
- [ ] Node wrappers, `graph.py`, Track B branch, `compare` node computing agreement
- [ ] Checkpointing, `--resume`

### Phase D: CLI [T4]
- [ ] Commands, options, exit codes, Rich rendering
- [ ] **Dual-track presentation** - both verdicts and where they differ
- [ ] **Picks before recommendations.** The rater must not see either engine's verdict before making their own. With two engines now offering opinions this matters more, not less.

### Phase E: Governance and tests [T5]
- [ ] CLAUDE.md rules 1 and 2 amended, superseded text `Deprecated` in place
- [ ] Boundary check reworked to a `rules/`+`models/` purity check; test enforces
- [ ] `.env.example`, `pyproject.toml` providers; `ANTHROPIC_API_KEY` deprecated in place
- [ ] Fixtures for Track B disagreement and the degradation path

## Current status

- Phase 3 complete at `339cc94`; 19 fixtures green; all four gates exit 0
- Phases A-E: pending
