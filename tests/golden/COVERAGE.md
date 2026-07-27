# Golden fixture coverage matrix

Reconciles `tests/golden/*.yaml` against `criteria/project-criteria.md`
(clause by clause, `{CRIT-n}`) and against every finding code in
`docs/RULES_SPEC.md` section 4 (`{RULE-16}`..`{RULE-23}`, 34 codes total).

Method: this matrix was built by reading each fixture's `expect:` block and
each fixture's authoring comment, then reading `criteria/project-criteria.md`
and `docs/RULES_SPEC.md` section 4 directly to check conditions. It was
**not** built by running the engine and recording whatever findings came
out — that would make the matrix describe current behavior instead of
required behavior, exactly the anti-pattern `team_plan.md`'s ANTI-DRIFT RULE
warns against for fixtures themselves. Where a finding is *structurally
implied* by a fixture's state but the fixture's `expect:` block does not
assert it, this is called out explicitly as "fires, unasserted" — a gap in
test strength, not a claim that the engine is wrong.

An honest gap is listed as **NOT COVERED**. A matrix with no gaps would be
lying; see CLAUDE.md: "A matrix that silently drifts is worse than no
matrix, because it looks true when it is not."

**Audit log (2026-07-26, post-review):** the lead caught a real drift on
first review — this row's `ex2_cutoff` cell claimed `clicks` coverage while
the fixture only flagged `cutoff`. `ex2_cutoff.yaml` was corrected to flag
`[cutoff, clicks]` (matching `criteria/worked-examples.md` Example 2's prose,
"cuts off abruptly and has a small pop", which the fixture's `best`/`worst`
text already carried but the flag did not), and its `expect.draft_contains`
sentence-1 string was re-derived by hand from `RULES_SPEC.md` section 3's
`joined()` two-item format ({RULE-47}), not by running the engine and
copying its output. Every other cell asserting a fixture's flags, picks, or
preflight fields was then re-checked line-by-line against the actual YAML
files (via direct reads and a `grep`/small script pass over all 13
fixtures, not by re-running the engine's decisions) — 45 distinct claims
audited across the 11 `{CRIT-n}` clause rows and the 34 finding-code rows,
1 wrong (the `clicks` cell, now fixed) and 1 ambiguously worded (the
`{CRIT-4}` `ex3_owls` cell, now clarified to name `premise_redteam`
explicitly rather than implying the raw `false_premise` key fires).

## Fixture inventory

| id | Owner | EVAL id | Source |
|---|---|---|---|
| `ex1_houseplant` | T6 | `EVAL-1` | `criteria/worked-examples.md` Example 1 |
| `ex2_cutoff` | T6 | `EVAL-2` | Example 2 |
| `ex3_owls` | T6 | `EVAL-3` | Example 3 (copied verbatim from `EVAL_SPEC.md`'s own worked YAML) |
| `ex4_neighbour_prefer_a` | T6 | `EVAL-4` | Example 4, "prefer A" branch |
| `ex4_neighbour_prefer_b` | T6 | `EVAL-5` | Example 4, "prefer B" branch |
| `audit_exercise_charisma` | T6 | `EVAL-6` | "Audit exercise" |
| `contradiction_both_good_audio` | T7 | `EVAL-7` | Adversarial |
| `contradiction_prefers_gated` | T7 | `EVAL-8` | Adversarial |
| `contradiction_dimensions_split` | T7 | `EVAL-9` | Adversarial |
| `turns_short_and_mismatched` | T7 | `EVAL-10` | Adversarial |
| `slight_noise_not_penalized` | T7 | `EVAL-11` | Adversarial |
| `empty_state` | T7 | `EVAL-12` | Adversarial |
| `both_sides_breach` | T7 | `EVAL-13` | Adversarial |

## `criteria/project-criteria.md` clause coverage

| Clause | Covering fixtures | Notes |
|---|---|---|
| `{CRIT-1}` North Star | `ex1_houseplant`, `ex2_cutoff`, `ex4_neighbour_prefer_a/b`, `audit_exercise_charisma`, `both_sides_breach`, `contradiction_dimensions_split`, `slight_noise_not_penalized`, `turns_short_and_mismatched` | Sentence 1 / Sentence 8 draft templates cite "the project's North Star" in every fixture whose verdict is decided. Not independently testable as its own code path; it is prose the draft always carries. |
| `{CRIT-2}` Hierarchy | `ex1_houseplant` (Naturalness decides), `ex4_neighbour_prefer_b`/`both_sides_breach` (Utility decides after Naturalness ties), `ex2_cutoff`/`ex3_owls`/`contradiction_prefers_gated` (threshold displaces naturalness) | Audio-decides branch (Naturalness and Utility both tie, Audio breaks it) has **NOT COVERED** — no fixture reaches the third rung of Step 2 without a threshold gate. |
| `{CRIT-3}` Dimensions and options | All 13 fixtures exercise `A`/`B`/`TIE` picks; `both_sides_breach` exercises `BAD` for `picks.overall` | `Pick.BAD` for a *dimension* pick (`naturalness`/`utility`/`audio` == `"BAD"`, i.e. "Both Bad" on a single dimension rather than overall) is **NOT COVERED** by any fixture. `task_success == "fail"` is also **NOT COVERED** — no fixture uses it. |
| `{CRIT-4}` Threshold breaches | `ex2_cutoff` (`cutoff` and `clicks`, both on `b.threshold_audio`), `ex3_owls` ("accepting a false premise", via the derived `premise_redteam` key — not the raw `false_premise` key, which no fixture sets directly), `contradiction_prefers_gated` (`hallucination`), `contradiction_both_good_audio` (`clicks`), `both_sides_breach` (`instruction_failure`, `distortion`) | `dropout` (threshold_audio), the raw `false_premise` key (as opposed to its derived `premise_redteam` sibling) and the derived `notable_noise` are **NOT COVERED** by any fixture. |
| `{CRIT-5}` Audio tolerance | `ex2_cutoff`, `contradiction_both_good_audio` (illegal "Both Good"), `slight_noise_not_penalized` (tolerance, no penalty) | Fully covered both directions (penalized vs tolerated). |
| `{CRIT-6}` Error clusters | `ex1_houseplant` (`over_structured` is Naturalness evidence, not a cluster), `ex4_neighbour_prefer_a/b` (`ignores_interruption`, `embodied`), `audit_exercise_charisma` (`interrupts_user`, `ignores_interruption`, `embodied`) | `repetitive`, `degradation`, `awkward_silence` and `speech_recognition` clusters are **NOT COVERED** by any required or adversarial fixture. `robotic_intonation` (clips-mode Naturalness evidence, `over_structured`'s sibling) is also **NOT COVERED** directly, though the same carve-out mechanism is proven by `over_structured` in `ex1_houseplant`. |
| `{CRIT-7}` Scenario awareness / pushback | `ex3_owls` (`PUSHBACK_IS_SUCCESS`) | `PREMISE_HEDGED` and `PREMISE_UNRECORDED` (both `{RULE-18}` §4.3) are **NOT COVERED**. |
| `{CRIT-8}` Conversation-mode requirements | `ex4_neighbour_prefer_a/b`, `audit_exercise_charisma` (all preflight items satisfied, turns=4 both sides, 1:1 consistency), `turns_short_and_mismatched` (turn minimum violated + mismatch, single combined error) | Preflight *failure* cases (`SETUP_HEADPHONES`, `SETUP_PANNING`, `AUDIO_NOT_ISOLATED`, `PROMPTS_NOT_EQUIVALENT`, `PERSONA_NOT_HELD`, `NO_INTERRUPTION_TEST`) are **NOT COVERED** — every conversation-mode fixture sets every `Preflight` field `true`. `TURNS_MISMATCH` (both sides clear 4 but counts differ) is **NOT COVERED** — the only turns-mismatch fixture also drops below the 4-turn floor, which is a deliberate, different code path (`TURNS_BELOW_MIN`'s combined-fact branch, `{EVAL-10}`). Skip (Technical Issue) is **NOT COVERED**. |
| `{CRIT-9}` Justification contract (`{CRIT-9.1}`-`{CRIT-9.5}`) | All six required fixtures assert `draft_contains` substrings for preference (9.1), hierarchy reference (9.2), both-sides evidence (9.3), and — where applicable — the threshold statement (9.4, `ex2_cutoff`/`ex3_owls`/`both_sides_breach`) and named clusters (9.5, `ex4_neighbour_prefer_a/b`/`audit_exercise_charisma`) | Fully covered across the required set; no single fixture needs to carry all five simultaneously since RULES_SPEC's sentence templates are conditional. |
| `{CRIT-10}` Common failures | `contradiction_dimensions_split` ("justification contradicts the dimension picks" -> `DIMENSIONS_CONTRADICT`), `contradiction_both_good_audio` ("Both Good on Audio Quality when one side has an obvious artifact"), `ex3_owls` (misreading pushback as a refusal, guarded against by `PUSHBACK_IS_SUCCESS`) | "Speaking to the model like a generic assistant / opening with 'As an AI...'" is a rater-behavior failure about the *model's own speech*, not something derivable from the rater's structured notes/flags — there is no `{RULE-n}` finding code for it (confirmed against RULES_SPEC section 4's full list) and it is out of the deterministic engine's reach. Not a fixture gap; a scope boundary. |
| `{CRIT-11}` Final review | N/A | This is a rater self-check performed before submission, not an engine output. No `{RULE-n}` finding models it, so there is nothing for a fixture to assert. |

## `RULES_SPEC.md` section 4 finding-code coverage (34 codes)

### 4.1 Setup and consistency — conversation mode only (`{RULE-16}`)

| Code | Severity | Covering fixture | Status |
|---|---|---|---|
| `SETUP_HEADPHONES` | error | — | **NOT COVERED** |
| `SETUP_PANNING` | warning | — | **NOT COVERED** |
| `AUDIO_NOT_ISOLATED` | warning | — | **NOT COVERED** |
| `TURNS_BELOW_MIN` | error | `turns_short_and_mismatched` | covered (combined with mismatch fact, per `{EVAL-10}`) |
| `TURNS_MISMATCH` | error | — | **NOT COVERED** (needs both sides >= 4 turns but unequal counts; no such fixture exists) |
| `TURNS_OK` | ok | `ex4_neighbour_prefer_a`, `ex4_neighbour_prefer_b`, `audit_exercise_charisma` | covered |
| `PROMPTS_NOT_EQUIVALENT` | error | — | **NOT COVERED** |
| `PERSONA_NOT_HELD` | warning | — | **NOT COVERED** |
| `NO_INTERRUPTION_TEST` | info | — | **NOT COVERED** |

### 4.2 Evidence — both modes (`{RULE-17}`)

| Code | Severity | Covering fixture | Status |
|---|---|---|---|
| `NOTES_MISSING` | error | `empty_state` | covered |
| `NOTES_IMBALANCED` | warning | — | **NOT COVERED** |
| `EVIDENCE_MISSING` | warning | `empty_state` (structurally, both `a.best`/`b.best` empty) | fires, unasserted — `empty_state`'s `expect:` only asserts `NOTES_MISSING` per `{RULE-43}`'s reconciliation note; it does not assert `EVIDENCE_MISSING` either way |
| `PROMPT_MISSING` | warning | `empty_state` (structurally, clips mode with `context.prompt` empty) | fires, unasserted, same reason |
| `GROUND_TRUTH_MISSING` | info | — | **NOT COVERED** (no `redteam`/`premise` fixture omits `ground_truth`; `ex3_owls` sets it) |

### 4.3 Scenario inversion (`{RULE-18}`)

| Code | Severity | Covering fixture | Status |
|---|---|---|---|
| `PUSHBACK_IS_SUCCESS` | ok | `ex3_owls` | covered |
| `PUSHBACK_PENALIZED` | warning | — | **NOT COVERED** (needs a side with `premise_handling: pushback` that *also* carries a `threshold_utility` flag) |
| `PREMISE_ACCEPTED` | error | `ex3_owls` | covered |
| `PREMISE_HEDGED` | info | — | **NOT COVERED** |
| `PREMISE_UNRECORDED` | info | — | **NOT COVERED** |

### 4.4 Audio (`{RULE-19}`)

| Code | Severity | Covering fixture | Status |
|---|---|---|---|
| `AUDIO_BOTH_GOOD_ILLEGAL` | error | `ex2_cutoff`, `contradiction_both_good_audio` | covered |
| `AUDIO_PICK_CONTRADICTS` | error | — | **NOT COVERED** (needs `picks.audio` set to the side that actually carries `threshold_audio`; every threshold-audio fixture picks `TIE` or the clean side instead) |
| `AUDIO_SLIGHT_TOLERATED` | ok | `slight_noise_not_penalized` | covered |
| `AUDIO_BOTH_CLEAN` | info | `empty_state` (structurally: no audio flags, `picks.audio` unset/`None`) | fires, unasserted — condition requires `picks.audio is None`, which no fixture with an explicit `TIE` pick satisfies; `empty_state` is the only fixture where it is even reachable, and its `expect:` block does not name it |

### 4.5 Utility (`{RULE-20}`)

| Code | Severity | Covering fixture | Status |
|---|---|---|---|
| `UTILITY_PICK_CONTRADICTS` | error | — | **NOT COVERED** (needs `picks.utility` set to the side carrying `threshold_utility`; every threshold-utility fixture picks the clean side or `TIE` instead) |

### 4.6 Overall coherence (`{RULE-21}`)

| Code | Severity | Covering fixture | Status |
|---|---|---|---|
| `OVERALL_PREFERS_GATED` | error | `contradiction_prefers_gated` | covered |
| `OVERALL_DIVERGES` | warning | `both_sides_breach` | covered |
| `OVERALL_COHERENT` | ok | `ex1_houseplant`, `ex2_cutoff`, `ex3_owls`, `ex4_neighbour_prefer_a`, `ex4_neighbour_prefer_b`, `audit_exercise_charisma` | covered |
| `DIMENSIONS_CONTRADICT` | error | `contradiction_dimensions_split` | covered |
| `HIERARCHY_REVERSED` | warning | `contradiction_dimensions_split` (structurally: `picks.overall == "A"`, `picks.naturalness == "B"`, not gated) | fires, unasserted — the fixture's `expect:` block names `DIMENSIONS_CONTRADICT` in `findings_include` but does not list `HIERARCHY_REVERSED` in either `findings_include` or `findings_exclude`, even though the same state satisfies both codes' conditions. Flagged to T7 (owner of this fixture) in `team_findings.md`; not edited here since it is outside T6's file ownership. |
| `SUCCESS_FAIL_PREFERRED` | error | — | **NOT COVERED** (no fixture sets `task_success: fail` on any side) |
| `SUCCESS_PASS_WITH_THRESHOLD` | warning | — | **NOT COVERED** (no fixture pairs `task_success: pass` with a `threshold_utility` flag on the same side) |

### 4.7 Error clusters (`{RULE-22}`)

| Code | Severity | Covering fixture | Status |
|---|---|---|---|
| `CLUSTERS_TO_REPORT` | info | `ex4_neighbour_prefer_a`, `ex4_neighbour_prefer_b`, `audit_exercise_charisma` | covered, including the per-side emission shape (one finding per qualifying side) |
| `PREFERRED_HAS_CLUSTERS` | warning | `ex4_neighbour_prefer_a`, `audit_exercise_charisma` (fires); `ex4_neighbour_prefer_b` (correctly excluded — B is preferred and carries no clusters) | covered in both directions |

`{RULE-22.1}` (naturalness-scored entries excluded from `CLUSTERS_TO_REPORT`) is covered by `ex1_houseplant`'s explicit `findings_exclude: [CLUSTERS_TO_REPORT]` alongside `error_clusters: [over_structured]`.

### 4.8 Skip (`{RULE-23}`)

| Code | Severity | Covering fixture | Status |
|---|---|---|---|
| `TECHNICAL_SKIP` | warning | — | **NOT COVERED** (no fixture sets `context.skip_reason`) |

## Summary of gaps

Not covered by any current fixture (18 of 34 codes untested one way or the
other, 3 more fire but are unasserted in the one fixture that reaches
them):

- `SETUP_HEADPHONES`, `SETUP_PANNING`, `AUDIO_NOT_ISOLATED`, `PROMPTS_NOT_EQUIVALENT`, `PERSONA_NOT_HELD`, `NO_INTERRUPTION_TEST` — every preflight-failure path in conversation mode.
- `TURNS_MISMATCH` — the "both clear 4, counts still differ" path, distinct from `turns_short_and_mismatched`'s below-minimum path.
- `NOTES_IMBALANCED`, `GROUND_TRUTH_MISSING`.
- `PUSHBACK_PENALIZED`, `PREMISE_HEDGED`, `PREMISE_UNRECORDED`.
- `AUDIO_PICK_CONTRADICTS`, `UTILITY_PICK_CONTRADICTS`.
- `SUCCESS_FAIL_PREFERRED`, `SUCCESS_PASS_WITH_THRESHOLD`.
- `TECHNICAL_SKIP`.
- Dimension-level `Pick.BAD` (as opposed to overall `Pick.BAD`, which `both_sides_breach` covers).
- The Step 2 "Audio decides" hierarchy branch (Naturalness and Utility both tie or are Both Bad, Audio breaks it, no threshold gate) — `{RULE-15}`.
- `EVIDENCE_MISSING`, `PROMPT_MISSING`, `AUDIO_BOTH_CLEAN` fire inside `empty_state` but are not asserted by name; `HIERARCHY_REVERSED` fires inside `contradiction_dimensions_split` but is not asserted by name.

None of these are silently assumed covered elsewhere in this document. Closing
them requires new adversarial fixtures or expanded `expect:` blocks on
existing ones (the latter for the three "fires, unasserted" cases and
`HIERARCHY_REVERSED`) — both outside `T6-fixtures-required`'s file ownership
(`ex1`..`ex4b`, `audit_exercise_charisma`) except where noted, and are
reported to `T7-fixtures-adversarial` and the lead rather than actioned here.
