# Evaluation and regression specification

Version: 1.2.0
Last updated: 2026-07-26

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
