# Build plan

Version: 1.0.0
Last updated: 2026-07-26

Ordered so that the engine is provably correct before anything is wired to it. Each phase ends with something runnable and tested.

Delegate each phase to the agent named in its heading. Read that phase's spec before writing code.

---

## Phase 1 — Criteria and catalogues · `criteria-keeper`

Deliverables:
- `criteria/project-criteria.md` and `criteria/worked-examples.md` reviewed and treated as frozen source of truth.
- `src/s2s_harness/rules/catalog.py` — the catalogues from `RULES_SPEC` §1 as typed constants, with `scored_as` set on `robotic_intonation` and `over_structured`.
- Mode profiles selecting which catalogue entries apply to `conversation` vs `clips`.

Done when: every display string reads correctly when spliced into `"{Side} had {display}"`.

## Phase 2 — State schema · `graph-architect`

Deliverables:
- `src/s2s_harness/models/state.py` — every model in `GRAPH_SPEC` §1.
- Validators: turn counts non-negative; flag keys exist in the catalogue; derived fields rejected on input.

Done when: `EvaluationState` round-trips through JSON losslessly and rejects an unknown flag key.

## Phase 3 — The engine · `rules-engine-dev`

The heart of the project. No I/O, no imports beyond stdlib and Pydantic.

Deliverables:
- `rules/normalize.py`, `rules/decide.py`, `rules/audit.py`, `rules/draft.py`, `rules/scanner.py`
- Exactly the rules in `RULES_SPEC` §§2–6 — no extras, no shortcuts.

Done when: every fixture in `EVAL_SPEC` passes, `test_determinism` passes, and the six invariants in `RULES_SPEC` §7 hold.

> Reconciliation note: an earlier draft of this line said "the seven invariants". `RULES_SPEC` §7's heading number (`7.`) is the section number, not an invariant count — the section has always enumerated six (`RULE-40` through `RULE-45`). No seventh invariant was ever dropped; this was a miscount in this file, corrected here rather than by adding an invariant to reach the stated number.

**Build the fixtures first.** Write `tests/golden/*.yaml` from the worked examples before writing `decide`, so the engine is developed against the known-correct answers rather than validated after the fact.

## Phase 4 — Graph · `graph-architect`

Deliverables:
- `nodes/` implementations wrapping the pure functions.
- `graph.py` — topology from `GRAPH_SPEC` §3, `should_polish` as a pure predicate.
- `nodes/polish.py` — the single sanctioned call site, with draft-hash caching and silent fallback to the deterministic draft.
- `MemorySaver`, and `SqliteSaver` behind `--resume`.

Done when: the graph produces the same verdict and draft as calling the rules functions directly, `--no-llm` yields complete output, and `test_token_boundary` passes.

## Phase 5 — CLI · `cli-dev`

Deliverables: every command and option in `CLI_SPEC`, Rich rendering, exit codes.

Done when: a full clip evaluation can be completed from a cold terminal without reading the docs, and `--json` output matches the state dump exactly.

## Phase 6 — STT · `stt-engineer`

Deliverables: provider protocol, `GeminiTranscriber`, `GoogleCloudSTT`, `NullTranscriber`, phrase-hint data file, `--dictate` capture, failure handling per `STT_SPEC` §8.

Done when: a dictated Spanish note produces a transcript whose terms the scanner picks up, and a missing credential fails loudly at startup.

> Blocked on the operator supplying credentials. Build against recorded fixtures until then; the provider protocol means nothing downstream waits on this.

## Phase 7 — Bridge and front ends · `bridge-dev`

Deliverables: FastAPI app, endpoints per `BRIDGE_SPEC`, the two HTML files stripped of their duplicated engines and pointed at `/evaluate`, `web/index.html` chooser.

Done when: `test_parity` passes — the bridge and the CLI produce byte-identical verdicts, finding sets and drafts for every fixture.

**Do not begin before Phase 3 is green.** Porting the front ends against an unstable engine means porting twice.

## Phase 8 — Hardening · `eval-runner` + `token-auditor`

- Full suite green, including determinism, parity and token-boundary.
- `token-auditor` sweep confirming no model call outside `nodes/polish.py`.
- `s2s selftest` wired to the golden suite so a rater can verify their install.

---

## Sequencing notes

- **Phases 1–3 are the critical path.** Everything else is transport around a correct engine.
- Phases 5, 6 and 7 are independent of one another once Phase 4 lands, and can run in parallel across agents.
- Do not start Phase 7 early to "get the UI working". The front ends already work today; their value in this repo is only realized once they stop carrying their own copy of the rules.

## Definition of done for the whole project

1. `uv run s2s clips --no-llm` produces a complete, submittable justification with zero network calls.
2. All golden fixtures pass, including the two defensible-either-way Example 4 variants.
3. The bridge and CLI agree byte-for-byte.
4. Grep proves exactly one model call site.
5. A rater who has never seen the repo can complete an evaluation from `README.md` alone.
