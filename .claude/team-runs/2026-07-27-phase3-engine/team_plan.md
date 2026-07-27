# Team Plan: Phase 3 — The deterministic engine

## Goal

Build the five pure rules modules and the golden suite that gates every future merge, so that every fixture in `EVAL_SPEC` passes, `test_determinism` passes, and the six invariants {RULE-40} to {RULE-45} hold.

## Ground rules for every teammate

1. **Read this file before any major decision.** Your context is volatile; this file is not.
2. **Cite a `{RULE-n}` or `{EVAL-n}` in every deliverable.** The specs now carry 189 stable IDs. If no ID covers what you are building, that is a spec bug: report it to T1-spec-gaps, do not invent behavior.
3. **Stay inside your file ownership.** Cross-boundary needs go to the owner via SendMessage, never by editing their files, never relayed through the lead.
4. **Write findings to `team_findings.md` immediately**, after at most 2 search/read operations. Do not batch.
5. **Log actions to `team_progress.md`** as you go.
6. **Run `graphify update .` before marking any task complete.**
7. **Write a completion marker to `team_progress.md` as your FINAL action**, in the form `- [T-n] COMPLETE: <one-line summary>`. In Wave 1 several teammates went idle without reporting and silence was indistinguishable from success. Do not repeat that.
8. **No emojis, no em-dashes** in code, comments, specs or draft text.
9. **Spanish and English both matter.** Every scanner pattern and every fixture touching notes covers both.
10. **3-Strike protocol.** Two failed attempts, log both and try a different method. Third failure, message the lead.

## THE ANTI-DRIFT RULE (non-negotiable)

Fixtures are authored from `criteria/worked-examples.md` and the specs ONLY.

**No fixture author may run the engine and paste its output into an `expect:` block.** BUILD_PLAN warns about exactly this. The golden suite is the merge gate for the entire project; a gate derived from the thing it gates verifies nothing. Any expected value that cannot be traced to a worked example or a `{RULE-n}` is rejected at review.

Engine authors: if a fixture disagrees with your implementation, that is a conversation with T2-fixtures and possibly a spec bug. It is NOT permission to edit the fixture.

## Non-negotiable design rules (from CLAUDE.md)

- **Zero LLM calls anywhere in `rules/`.** stdlib and Pydantic only. No network, no I/O, no clock, no randomness.
- Exactly one sanctioned LLM call site, `nodes/polish.py`, which does not exist yet. Do not create a second.
- **Never invent observations.** Missing detail becomes exactly `【what the rater must add】`.
- **No magic literals in `rules/`.** Every threshold, cluster name and display string traces to `criteria/project-criteria.md` or a `{RULE-n}`, cited in a comment.
- Type everything. `Literal` for closed sets. Never widen a `Literal` to `str` to make something pass.
- **Determinism.** No set iteration or dict reordering in any output path. `test_determinism` runs every fixture 50 times asserting byte-identical verdict, trace, finding codes and draft.

## Six underspecifications being closed by T1 FIRST

These block byte-exact work. T1 broadcasts each resolution the moment it lands; do not wait for T1's whole phase, and do not guess in the meantime.

| # | Gap |
|---|---|
| 1 | TIE/BAD early-return paragraph {RULE-25} described, never quoted. No worked example covers TIE or BAD. |
| 2 | Step 2 hierarchy-walk trace strings not given, though §3 says traces are "part of the contract" and fixtures assert on them. |
| 3 | {RULE-12} both-sides-breach trace has no verbatim template, unlike the other three gate cases. |
| 4 | `Finding.label` exists in GRAPH_SPEC section 1 but no label string is defined for any of the 34 codes. |
| 5 | Sentence 3 variant 1 has a literal `gap(...)` ellipsis, unlike `evW`/`evL` which have exact fallback text. |
| 6 | `speech_recognition` has no scanner row; the two tone signals {RULE-35} have no patterns enumerated. |

Plus: `EVAL_SPEC` names the fixture `ex3_owls` in its table but `ex3_owls_false_premise` in the worked YAML. One id, chosen once, by T1.

## Correction carried from reconnaissance

`RULES_SPEC` section 4 defines **34 finding codes, not 29**. Counted by subsection: 4.1=9, 4.2=5, 4.3=5, 4.4=4, 4.5=1, 4.6=7, 4.7=2, 4.8=1.

## Team Composition

| Teammate | Owns | Spec range |
|---|---|---|
| lead (orchestrator) | nothing; reviews, verifies, coordinates | — |
| T1 `spec-gaps` | `docs/RULES_SPEC.md`, `docs/EVAL_SPEC.md` | the six gaps |
| T2 `fixtures` | all of `tests/` | {EVAL-1}..{EVAL-16} |
| T3 `normalize-decide` | `rules/normalize.py`, `rules/decide.py` | {RULE-5}..{RULE-15} |
| T4 `audit` | `rules/audit.py` | {RULE-16}..{RULE-23} |
| T5 `draft-scanner` | `rules/draft.py`, `rules/scanner.py` | {RULE-24}..{RULE-39} |

Already in the tree from Wave 1, do not disturb: `rules/catalog.py` (T2 of Wave 1), `models/state.py`, `tests/test_layering.py`.

## Phases

### Phase A: Close the spec gaps [T1] — blocks others, do first
- [ ] Resolve gaps 1 through 6, deriving wording from `criteria/project-criteria.md` and the worked examples. Invent no new rule.
- [ ] Resolve the `ex3_owls` id discrepancy.
- [ ] Bump Version headers on both owned specs.
- [ ] Broadcast each resolution by SendMessage AS IT LANDS.
- **Gate:** orchestrator reviews read-only and may reject.

### Phase B: Fixtures [T2]
- [ ] 13 fixtures: 6 required {EVAL-1}..{EVAL-6}, 7 adversarial {EVAL-7}..{EVAL-13}
- [ ] `test_determinism.py` {EVAL-15}, `test_token_boundary.py` {EVAL-16}
- [ ] `COVERAGE.md` reconciling fixtures against `criteria/project-criteria.md` clause by clause, same change

### Phase C: normalize + decide [T3]
- [ ] {RULE-5}..{RULE-9} normalize; {RULE-10}..{RULE-15} threshold gate and hierarchy walk
- [ ] {RULE-40} never raises on any input including empty state
- [ ] {RULE-41} pure function of `(a.threshold_all, b.threshold_all, picks)` and nothing else
- [ ] {RULE-44} `clean` to `slight` changes no verdict and adds no flag

### Phase D: audit [T4]
- [ ] All 34 codes, exact severities and conditions, sorted error to warning to info to ok
- [ ] {RULE-22.1} `CLUSTERS_TO_REPORT` excludes `scored_as="naturalness"` entries
- [ ] {RULE-43} empty state produces zero error findings
- [ ] {RULE-45} `pushback` never contributes a negative finding

### Phase E: draft + scanner [T5]
- [ ] Eight sentence slots with every variant; `frag()`/`gap()` {RULE-24}
- [ ] The "Beyond that..." sentence must not re-list an already-cited category ({EVAL-2} asserts this)
- [ ] {RULE-42} `build_draft` returns non-empty whenever `verdict.overall` is set
- [ ] Scanner: 15 keys, Spanish and English, {RULE-36}..{RULE-39}

## Current Status

- Wave 1: complete, pushed at 72c25ac
- Phases A-E: pending
