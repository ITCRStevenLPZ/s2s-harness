# Evaluation and regression specification

The four worked examples in the project training material are the specification of correct behavior. They are encoded as fixtures and treated as a contract.

## Golden fixtures

`tests/golden/*.yaml`. Each file holds the input state and the expected outputs.

```yaml
id: ex3_owls_false_premise
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

| id | Source | Asserts |
|---|---|---|
| `ex1_houseplant` | Example 1 | Naturalness decides when both sides are clean; over-structured delivery is Naturalness evidence, not a reportable cluster |
| `ex2_cutoff` | Example 2 | Audio threshold gate; `Both Good` becomes illegal; the "Beyond that…" sentence does not re-list the cited category |
| `ex3_owls` | Example 3 | Utility threshold gate; correct pushback scores as success; naturalness favouring the gated side is acknowledged, not ignored |
| `ex4_neighbour_prefer_a` | Example 4 | Clusters reported while still preferring that side; the trade-off sentence appears |
| `ex4_neighbour_prefer_b` | Example 4 | The alternative defensible vote produces coherent output with the same clusters flagged |
| `audit_exercise_charisma` | Knowledge-check scenario | Interruption + ignored-interruption + embodied claim are three flags; no threshold breach; A remains a legal overall pick |

### Adversarial fixtures

| id | Asserts |
|---|---|
| `contradiction_both_good_audio` | `AUDIO_BOTH_GOOD_ILLEGAL` fires |
| `contradiction_prefers_gated` | `OVERALL_PREFERS_GATED` fires as an error |
| `contradiction_dimensions_split` | `DIMENSIONS_CONTRADICT` fires when the loser wins 2 of 3 |
| `turns_short_and_mismatched` | One error carrying both facts, not two |
| `slight_noise_not_penalized` | Verdict identical to the clean-audio variant; no audio flag added |
| `empty_state` | `decide` returns `overall=None`, raises nothing, produces zero errors |
| `both_sides_breach` | Falls through to the hierarchy; `Both Bad` defensible |

## Regression policy

- A change that flips a golden fixture is **wrong by default**. To change one, first change `criteria/project-criteria.md` and state which project rule changed, in the same commit.
- `eval-runner` runs the suite. Cheap model, mechanical job.
- CI (or a pre-commit hook) runs `pytest tests/golden` on any change under `src/s2s_harness/rules/`.

## Determinism test

`test_determinism.py`: run every fixture 50 times, assert byte-identical verdict, trace, finding codes and draft. Catches accidental set/dict ordering leaks — the most likely way non-determinism sneaks into a pure engine.

## Token-boundary test

`test_token_boundary.py`: walk the AST of everything under `src/s2s_harness/` except `nodes/polish.py`, and fail on any import of an LLM SDK or any call matching the client patterns. This is the executable form of the rule in `CLAUDE.md`; `token-auditor` runs the same check.

## STT tests

Provider adapters are tested against recorded fixtures with `responses`/`vcr`-style playback — no live API calls in the suite. One test asserts that phrase hints are actually passed through to the provider config, since a silently dropped hint list degrades recall in a way no other test would catch.

## What is not tested

Prose quality from `polish`. It is non-deterministic by nature. What *is* tested is that `polish` never changes the verdict, never removes a `【placeholder】`, and never runs when a blocking error is present — assertions about the harness around the model, not about the model.
