# Evaluation and regression specification

Version: 1.4.0
Last updated: 2026-07-26

**Wave 2, fourth pass:** closed the last `{EVAL-24}` gap `COVERAGE.md` found after the `EVAL-19`-`EVAL-23` fixtures landed: `{RULE-15}`'s Step 2 "no-separating-evidence" fallback (naturalness `TIE`/`BAD`, utility and audio both inconclusive too, `verdict.overall` becomes `TIE`/`BAD` from the walk itself) had no covering fixture. New adversarial-fixture row `hierarchy_no_separating_evidence` (`EVAL-25`) closes it and, as a side effect, is the first fixture in the suite to exercise `{RULE-25}`'s TIE/BAD early-return paragraph, which had no fixture either. Filed by `T6-fixtures-required` since `T1-spec-gaps` has terminated and this file is otherwise orphaned; kept minimal and additive, no existing row reworded or renumbered.

**Wave 2, third pass:** the user ruled on the Tier-1-coverage question raised by `T6-fixtures-required`'s honest `COVERAGE.md` (24 of 34 codes not fully covered, against `CLAUDE.md`'s "100% of rules-engine branches" claim). Neither "make it literally 100%" nor "leave the false claim" — a stated, checkable threshold instead: every error-severity finding code, and every threshold-gate/hierarchy-walk branch, must have a fixture; `info`/`ok` need not. New `## Coverage threshold {EVAL-24}` section states this as a requirement. Five new adversarial-fixture rows (`EVAL-19`-`EVAL-23`) close the six error-code gaps and the one hierarchy-branch gap `COVERAGE.md` found. `CLAUDE.md` itself is not touched here — operator-managed, the lead is handling that line under the user's approval.

**Wave 2, second pass:** updated the `empty_state` / `EVAL-12` row to match `RULES_SPEC` 1.2.0's narrowed `{RULE-43}` — `NOTES_MISSING` is expected to fire on that fixture and belongs in `findings_include`, not `findings_exclude`. No assertion about `decide()` itself changed.

**Wave 2 fix (this version):** reconciled the `ex3` fixture id — the worked YAML below said `ex3_owls_false_premise`, the required-fixtures table said `ex3_owls`. Standardized on `ex3_owls`, matching the naming convention of every other row in that table (`ex1_houseplant`, `ex2_cutoff`, `ex4_neighbour_prefer_a/b`, `audit_exercise_charisma` — short and thematic, not restating the `scenario_type` field that is already `premise` in the fixture body). No assertion, verdict or finding changed.

**ID convention:** `EVAL-n` trailing tag `{EVAL-n}`, assigned once per required fixture (in table order), then once per adversarial fixture (in table order), then once per test-category subsection (in document order). IDs are additive only; no fixture assertion below was reworded, reordered or removed to add them.

The four worked examples in the project training material are the specification of correct behavior. They are encoded as fixtures and treated as a contract.

## Golden fixtures

`tests/golden/*.yaml`. Each file holds the input state and the expected outputs.

```yaml
id: ex3_owls
mode: clips
context:
  prompt: "Why do owls sleep upside down like bats?"
  scenario_type: premise
  ground_truth: "Owls do not sleep upside down; bats do. Owls perch upright."
a:
  notes: "Suena fluido pero se la creyó e inventó una explicación."
  best: "fluent, easy delivery"
  worst: "it claims owls sleep upside down like bats and invents a reason"
  premise_handling: accepted
b:
  notes: "Corrigió la premisa con tacto y dio la alternativa correcta."
  best: "it corrects the premise without lecturing and gives the accurate alternative"
  worst: "marginally less lively than Clip A"
  premise_handling: pushback
picks: {naturalness: A, utility: B, audio: TIE, overall: B}
expect:
  verdict:
    overall: B
    driver: "Threshold — Utility"
    gated: true
    gated_side: A
  findings_include: [PREMISE_ACCEPTED, PUSHBACK_IS_SUCCESS, OVERALL_COHERENT]
  findings_exclude: [OVERALL_PREFERS_GATED, AUDIO_BOTH_GOOD_ILLEGAL]
  draft_contains:
    - "I prefer Clip B overall"
    - "cannot outweigh a threshold failure"
    - "counts as a success, not a refusal to help"
  draft_excludes:
    - "【"                       # every needed observation was supplied
```

### Required fixtures

| id | Source | Asserts | ID |
|---|---|---|---|
| `ex1_houseplant` | Example 1 | Naturalness decides when both sides are clean; over-structured delivery is Naturalness evidence, not a reportable cluster | `EVAL-1` |
| `ex2_cutoff` | Example 2 | Audio threshold gate; `Both Good` becomes illegal; the "Beyond that…" sentence does not re-list the cited category | `EVAL-2` |
| `ex3_owls` | Example 3 | Utility threshold gate; correct pushback scores as success; naturalness favouring the gated side is acknowledged, not ignored | `EVAL-3` |
| `ex4_neighbour_prefer_a` | Example 4 | Clusters reported while still preferring that side; the trade-off sentence appears | `EVAL-4` |
| `ex4_neighbour_prefer_b` | Example 4 | The alternative defensible vote produces coherent output with the same clusters flagged | `EVAL-5` |
| `audit_exercise_charisma` | Knowledge-check scenario | Interruption + ignored-interruption + embodied claim are three flags; no threshold breach; A remains a legal overall pick | `EVAL-6` |

### Adversarial fixtures

| id | Asserts | ID |
|---|---|---|
| `contradiction_both_good_audio` | `AUDIO_BOTH_GOOD_ILLEGAL` fires | `EVAL-7` |
| `contradiction_prefers_gated` | `OVERALL_PREFERS_GATED` fires as an error | `EVAL-8` |
| `contradiction_dimensions_split` | `DIMENSIONS_CONTRADICT` fires when the loser wins 2 of 3 | `EVAL-9` |
| `turns_short_and_mismatched` | One error carrying both facts, not two | `EVAL-10` |
| `slight_noise_not_penalized` | Verdict identical to the clean-audio variant; no audio flag added | `EVAL-11` |
| `empty_state` | `decide` returns `overall=None`, raises nothing; zero flag/pick-derived error findings per the narrowed `{RULE-43}` — `NOTES_MISSING` (and any other §4.1/§4.2 evidence/setup gate the fixture's mode triggers) is expected to fire and must appear in `findings_include`, not `findings_exclude` | `EVAL-12` |
| `both_sides_breach` | Falls through to the hierarchy; `Both Bad` defensible | `EVAL-13` |
| `contradiction_preflight_and_turns` | Conversation mode. `SETUP_HEADPHONES` (`not preflight.headphones`), `PROMPTS_NOT_EQUIVALENT` (`not preflight.equivalent_prompts`) and `TURNS_MISMATCH` (both sides clear 4 turns, counts differ — e.g. `a.turns=5`, `b.turns=6`, distinct from `turns_short_and_mismatched`'s below-floor case) all fire together from three structurally independent preflight/turn-count conditions in one fixture; all other preflight fields left `true` so no other §4.1 code fires incidentally | `EVAL-19` |
| `contradiction_audio_pick` | `AUDIO_PICK_CONTRADICTS` fires: `picks.audio` names the side carrying `threshold_audio` while the other side is clean | `EVAL-20` |
| `contradiction_utility_pick` | `UTILITY_PICK_CONTRADICTS` fires: `picks.utility` names the side carrying `threshold_utility` while the other side is clean | `EVAL-21` |
| `contradiction_success_fail_preferred` | Conversation mode. `SUCCESS_FAIL_PREFERRED` fires: the side named in `picks.overall` is marked `task_success: fail` | `EVAL-22` |
| `hierarchy_audio_decides` | Closes the `{RULE-15}` Step 2 gap `COVERAGE.md` found: `picks.naturalness: TIE`, `picks.utility: TIE`, neither side gated (`threshold_all` empty both sides), `picks.audio` names a side — `verdict.driver == "Audio Quality"` and `verdict.overall` matches `picks.audio` | `EVAL-23` |
| `hierarchy_no_separating_evidence` | Closes the last `{RULE-15}` Step 2 gap `COVERAGE.md` found: naturalness, utility and audio picks all `TIE`, neither side gated — `verdict.driver == "No separating evidence"` and `verdict.overall == "TIE"`. Also the first fixture to exercise `{RULE-25}`'s TIE/BAD early-return paragraph (distinct from `both_sides_breach`, whose `picks.overall: BAD` is a rater vote against a computed `verdict.overall` of `"B"`, never reaching this early return) | `EVAL-25` |

## Coverage threshold {EVAL-24}

Tier 1 does not claim literal 100% branch coverage. The user ruled on the honest gap `T6-fixtures-required`'s `COVERAGE.md` surfaced (24 of 34 finding codes not fully covered) with a stated, checkable bar instead of either extreme ("make it literally 100%" or "leave the false claim"):

**Every error-severity finding code in `RULES_SPEC.md` §4, and every threshold-gate and hierarchy-walk branch in `RULES_SPEC.md` §3, must have at least one covering fixture. `warning`, `info` and `ok` severity finding codes are not required by this gate.**

- The threshold/hierarchy branches in scope are: the four Step 1 gate cases (`{RULE-10}` A-gated, `{RULE-11}` B-gated, `{RULE-12}` both-breach, `{RULE-13}` both-clean) and the five Step 2 branches under `{RULE-15}` (naturalness-decides, naturalness-unset, utility-decides, audio-decides, no-separating-evidence).
- `warning`/`info`/`ok` codes are not in the "must" set because the "must" set is defined as error-severity codes plus branches — nothing broader. `COVERAGE.md` should keep recording their status honestly regardless; an uncovered `warning`/`info`/`ok` code does not fail this gate, but a silently-dropped row would still violate `CLAUDE.md`'s coverage-manifest mandate.

**Mechanical check:** read every `Code | Severity` row across `RULES_SPEC.md` §4.1-§4.8, filter to `Severity == error`; read the nine threshold/hierarchy branches listed above. For each one, `tests/golden/COVERAGE.md` must name a covering fixture id, not `NOT COVERED` and not a silent omission. If any in-scope item is missing or marked `NOT COVERED`, the gate is not met. This mirrors the exact wording now in `CLAUDE.md`'s Two-tier test gate section, so the two documents cannot silently drift apart on what "covers" means.

## Regression policy {EVAL-14}

- A change that flips a golden fixture is **wrong by default**. To change one, first change `criteria/project-criteria.md` and state which project rule changed, in the same commit.
- `eval-runner` runs the suite. Cheap model, mechanical job.
- CI (or a pre-commit hook) runs `pytest tests/golden` on any change under `src/s2s_harness/rules/`.

## Determinism test {EVAL-15}

`test_determinism.py`: run every fixture 50 times, assert byte-identical verdict, trace, finding codes and draft. Catches accidental set/dict ordering leaks — the most likely way non-determinism sneaks into a pure engine.

## Token-boundary test {EVAL-16}

`test_token_boundary.py`: walk the AST of everything under `src/s2s_harness/` except `nodes/polish.py`, and fail on any import of an LLM SDK or any call matching the client patterns. This is the executable form of the rule in `CLAUDE.md`; `token-auditor` runs the same check.

## STT tests {EVAL-17}

Provider adapters are tested against recorded fixtures with `responses`/`vcr`-style playback — no live API calls in the suite. One test asserts that phrase hints are actually passed through to the provider config, since a silently dropped hint list degrades recall in a way no other test would catch.

## What is not tested {EVAL-18}

Prose quality from `polish`. It is non-deterministic by nature. What *is* tested is that `polish` never changes the verdict, never removes a `【placeholder】`, and never runs when a blocking error is present — assertions about the harness around the model, not about the model.
