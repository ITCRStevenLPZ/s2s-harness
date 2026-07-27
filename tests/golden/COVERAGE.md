# Golden fixture coverage matrix

Reconciles `tests/golden/*.yaml` against `criteria/project-criteria.md`
(clause by clause, `{CRIT-n}`), against every finding code in
`docs/RULES_SPEC.md` section 4 (`{RULE-16}`..`{RULE-23}`, 34 codes total),
and against every threshold-gate / hierarchy-walk branch in section 3
(`{RULE-10}`..`{RULE-15}`, 9 branches), per the coverage bar in
`docs/EVAL_SPEC.md` `## Coverage threshold {EVAL-24}` (v1.3.0).

Method: this matrix was built by reading each fixture's `expect:` block and
each fixture's authoring comment, then reading `criteria/project-criteria.md`
and `docs/RULES_SPEC.md` sections 3-4 directly to check conditions. It was
**not** built by running the engine and recording whatever findings came
out — that would make the matrix describe current behavior instead of
required behavior, exactly the anti-pattern `team_plan.md`'s ANTI-DRIFT RULE
warns against for fixtures themselves. Where a finding is *structurally
implied* by a fixture's state but the fixture's `expect:` block does not
assert it, this is called out explicitly as "fires, unasserted" — a gap in
test strength, not a claim that the engine is wrong.

An honest gap is listed as **NOT COVERED**. A matrix with no gaps would be
lying; see CLAUDE.md: "A matrix that silently drifts is worse than no
matrix, because it looks true when it is not." The same principle cuts both
ways: a matrix that denies coverage that actually exists is equally untrue,
and the audit log below records one round of each kind of drift.

**Audit log (2026-07-26, round 2, post first review):** the lead caught a
real drift — this row's `ex2_cutoff` cell claimed `clicks` coverage while
the fixture only flagged `cutoff`. `ex2_cutoff.yaml` was corrected to flag
`[cutoff, clicks]` (matching `criteria/worked-examples.md` Example 2's prose,
"cuts off abruptly and has a small pop", which the fixture's `best`/`worst`
text already carried but the flag did not), and its `expect.draft_contains`
sentence-1 string was re-derived by hand from `RULES_SPEC.md` section 3's
`joined()` two-item format ({RULE-47}), not by running the engine and
copying its output. Every other cell asserting a fixture's flags, picks, or
preflight fields was then re-checked line-by-line against the actual YAML
files (via direct reads and a `grep`/small script pass over all 13
fixtures then in place, not by re-running the engine's decisions) — 45
distinct claims audited across the 11 `{CRIT-n}` clause rows and the 34
finding-code rows, 1 wrong (the `clicks` cell, now fixed) and 1
ambiguously worded (the `{CRIT-4}` `ex3_owls` cell, clarified to name
`premise_redteam` explicitly rather than implying the raw `false_premise`
key fires).

**Audit log (round 3, this version):** `docs/EVAL_SPEC.md` 1.3.0 added
`{EVAL-24}`'s coverage threshold (every error-severity code and every
`RULES_SPEC.md` §3 branch must have a fixture); T7 landed five new
fixtures at `a95e3dd` / renamed at `b0aa7fd` (`contradiction_preflight_and_turns`,
`contradiction_audio_pick`, `contradiction_utility_pick`,
`contradiction_success_fail_preferred`, `hierarchy_audio_decides`,
`EVAL-19`..`EVAL-23`) closing six previously-`NOT COVERED` error codes and
the Step 2 audio-decides branch. This matrix was last touched at `6e23500`,
before those fixtures existed, so it still read all six as `NOT COVERED` —
that is the mirror-image drift of round 2: denying coverage that now
exists. This version updates every affected row by reading the five new
fixture files directly (not by trusting their names or the lead's list —
one fixture is `contradiction_audio_pick`, matching, but the point was to
verify, not assume), runs the `{EVAL-24}` mechanical check in full for the
first time, and surfaces one genuine, previously-unnoticed gap the
mechanical check exists to catch: the Step 2 "no-separating-evidence"
(`TIE`/`BAD`) branch has **no covering fixture anywhere in the suite**. See
the `{EVAL-24}` mechanical check section below for the full accounting.

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
| `contradiction_preflight_and_turns` | T7 | `EVAL-19` | Coverage-threshold fixture, closes `SETUP_HEADPHONES`/`TURNS_MISMATCH`/`PROMPTS_NOT_EQUIVALENT` |
| `contradiction_audio_pick` | T7 | `EVAL-20` | Coverage-threshold fixture, closes `AUDIO_PICK_CONTRADICTS` |
| `contradiction_utility_pick` | T7 | `EVAL-21` | Coverage-threshold fixture, closes `UTILITY_PICK_CONTRADICTS` |
| `contradiction_success_fail_preferred` | T7 | `EVAL-22` | Coverage-threshold fixture, closes `SUCCESS_FAIL_PREFERRED` |
| `hierarchy_audio_decides` | T7 | `EVAL-23` | Coverage-threshold fixture, closes the Step 2 audio-decides branch |

## `criteria/project-criteria.md` clause coverage

| Clause | Covering fixtures | Notes |
|---|---|---|
| `{CRIT-1}` North Star | `ex1_houseplant`, `ex2_cutoff`, `ex4_neighbour_prefer_a/b`, `audit_exercise_charisma`, `both_sides_breach`, `contradiction_dimensions_split`, `slight_noise_not_penalized`, `turns_short_and_mismatched`, `contradiction_preflight_and_turns`, `contradiction_success_fail_preferred`, `hierarchy_audio_decides` | Sentence 1 / Sentence 8 draft templates cite "the project's North Star" in every fixture whose verdict is decided. Not independently testable as its own code path; it is prose the draft always carries. |
| `{CRIT-2}` Hierarchy | `ex1_houseplant` (Naturalness decides), `ex4_neighbour_prefer_b`/`both_sides_breach` (Utility decides after Naturalness ties), `hierarchy_audio_decides` (Audio decides after Naturalness and Utility both tie, no threshold gate), `ex2_cutoff`/`ex3_owls`/`contradiction_prefers_gated`/`contradiction_audio_pick`/`contradiction_utility_pick` (threshold displaces naturalness) | The Step 2 "no-separating-evidence" fallback (Naturalness TIE/BAD, Utility inconclusive, Audio inconclusive too — the walk reaches `Both Good`/`Both Bad` on its own, not via a threshold gate) is **NOT COVERED** by any fixture. See the `{EVAL-24}` mechanical check below — this is the one in-scope branch gap. |
| `{CRIT-3}` Dimensions and options | All 18 fixtures exercise `A`/`B`/`TIE` picks; `both_sides_breach` exercises `BAD` for `picks.overall`; `contradiction_success_fail_preferred` exercises `task_success: fail` | `Pick.BAD` for a *dimension* pick (`naturalness`/`utility`/`audio` == `"BAD"`, i.e. "Both Bad" on a single dimension rather than overall) is still **NOT COVERED** by any fixture — distinct from `verdict.overall == "BAD"`, which is also not reached by any fixture (the same gap named under `{CRIT-2}` above). |
| `{CRIT-4}` Threshold breaches | `ex2_cutoff` (`cutoff` and `clicks`, both on `b.threshold_audio`), `ex3_owls` ("accepting a false premise", via the derived `premise_redteam` key — not the raw `false_premise` key, which no fixture sets directly), `contradiction_prefers_gated` (`hallucination`), `contradiction_both_good_audio` (`clicks`), `both_sides_breach` (`instruction_failure`, `distortion`), `contradiction_audio_pick` (`distortion`, a second instance), `contradiction_utility_pick` (`instruction_failure`, a second instance) | `dropout` (threshold_audio), the raw `false_premise` key (as opposed to its derived `premise_redteam` sibling) and the derived `notable_noise` are **NOT COVERED** by any fixture. |
| `{CRIT-5}` Audio tolerance | `ex2_cutoff`, `contradiction_both_good_audio` (illegal "Both Good"), `slight_noise_not_penalized` (tolerance, no penalty) | Fully covered both directions (penalized vs tolerated). |
| `{CRIT-6}` Error clusters | `ex1_houseplant` (`over_structured` is Naturalness evidence, not a cluster), `ex4_neighbour_prefer_a/b` (`ignores_interruption`, `embodied`), `audit_exercise_charisma` (`interrupts_user`, `ignores_interruption`, `embodied`) | `repetitive`, `degradation`, `awkward_silence` and `speech_recognition` clusters are **NOT COVERED** by any fixture. `robotic_intonation` (clips-mode Naturalness evidence, `over_structured`'s sibling) is also **NOT COVERED** directly, though the same carve-out mechanism is proven by `over_structured` in `ex1_houseplant`. None of these are error-severity findings and none are `{RULE-n}` §3 branches, so they are outside `{EVAL-24}`'s "must" set, but are recorded here per `CLAUDE.md`'s coverage-manifest mandate. |
| `{CRIT-7}` Scenario awareness / pushback | `ex3_owls` (`PUSHBACK_IS_SUCCESS`) | `PREMISE_HEDGED` and `PREMISE_UNRECORDED` (both `{RULE-18}` §4.3, both `info`) are **NOT COVERED**; not required by `{EVAL-24}`. |
| `{CRIT-8}` Conversation-mode requirements | `ex4_neighbour_prefer_a/b`, `audit_exercise_charisma` (all preflight items satisfied, turns=4 both sides, 1:1 consistency), `turns_short_and_mismatched` (turn minimum violated + mismatch, single combined error), `contradiction_preflight_and_turns` (headphones not confirmed, prompts not confirmed equivalent, and a turns mismatch that clears the 4-turn floor on both sides — three independent 4.1 failures in one fixture), `contradiction_success_fail_preferred` (a legal-but-incoherent pick/task_success combination) | `SETUP_PANNING`, `AUDIO_NOT_ISOLATED`, `PERSONA_NOT_HELD` and `NO_INTERRUPTION_TEST` (all `warning`/`info`, not required by `{EVAL-24}`) are still **NOT COVERED** — every conversation-mode fixture leaves those four `Preflight` fields `true`. Skip (Technical Issue) is also **NOT COVERED** (`warning`, not required). |
| `{CRIT-9}` Justification contract (`{CRIT-9.1}`-`{CRIT-9.5}`) | All required fixtures assert `draft_contains` substrings for preference (9.1), hierarchy reference (9.2), both-sides evidence (9.3), and — where applicable — the threshold statement (9.4, `ex2_cutoff`/`ex3_owls`/`both_sides_breach`/`contradiction_audio_pick`/`contradiction_utility_pick`) and named clusters (9.5, `ex4_neighbour_prefer_a/b`/`audit_exercise_charisma`) | Fully covered across the required set; no single fixture needs to carry all five simultaneously since RULES_SPEC's sentence templates are conditional. |
| `{CRIT-10}` Common failures | `contradiction_dimensions_split` ("justification contradicts the dimension picks" -> `DIMENSIONS_CONTRADICT`), `contradiction_both_good_audio` ("Both Good on Audio Quality when one side has an obvious artifact"), `ex3_owls` (misreading pushback as a refusal, guarded against by `PUSHBACK_IS_SUCCESS`), `contradiction_success_fail_preferred` (preferring a side marked as failing the task) | "Speaking to the model like a generic assistant / opening with 'As an AI...'" is a rater-behavior failure about the *model's own speech*, not something derivable from the rater's structured notes/flags — there is no `{RULE-n}` finding code for it (confirmed against RULES_SPEC section 4's full list) and it is out of the deterministic engine's reach. Not a fixture gap; a scope boundary. |
| `{CRIT-11}` Final review | N/A | This is a rater self-check performed before submission, not an engine output. No `{RULE-n}` finding models it, so there is nothing for a fixture to assert. |

## `RULES_SPEC.md` section 3 threshold-gate / hierarchy-walk branch coverage (9 branches, `{EVAL-24}`)

| Branch | Covering fixture(s) | Status |
|---|---|---|
| `{RULE-10}` Step 1, A gated (`thr_a>0, thr_b==0`) | `contradiction_prefers_gated`, `contradiction_audio_pick`, `contradiction_utility_pick` | covered |
| `{RULE-11}` Step 1, B gated (`thr_b>0, thr_a==0`) | `ex2_cutoff`, `contradiction_both_good_audio` | covered |
| `{RULE-12}` Step 1, both breach (`thr_a>0 and thr_b>0`) | `both_sides_breach` | covered |
| `{RULE-13}` Step 1, both clean, falls through | `ex1_houseplant` (representative; also `ex4_neighbour_prefer_a/b`, `audit_exercise_charisma`, `contradiction_dimensions_split`, `slight_noise_not_penalized`, `turns_short_and_mismatched`, `empty_state`, `contradiction_preflight_and_turns`, `contradiction_success_fail_preferred`, `hierarchy_audio_decides`) | covered |
| `{RULE-15}` Step 2, naturalness-decides (`picks.naturalness in {A,B}`) | `ex1_houseplant` (representative; also `ex4_neighbour_prefer_a`, `audit_exercise_charisma`, `contradiction_dimensions_split`, `slight_noise_not_penalized`, `turns_short_and_mismatched`, `contradiction_preflight_and_turns`, `contradiction_success_fail_preferred`) | covered |
| `{RULE-15}` Step 2, naturalness-unset (`picks.naturalness is None`) | `empty_state` | covered |
| `{RULE-15}` Step 2, utility-decides (naturalness inconclusive, `picks.utility in {A,B}`) | `ex4_neighbour_prefer_b`, `both_sides_breach` | covered |
| `{RULE-15}` Step 2, audio-decides (naturalness and utility both inconclusive, `picks.audio in {A,B}`) | `hierarchy_audio_decides` | covered |
| `{RULE-15}` Step 2, no-separating-evidence fallback (naturalness TIE/BAD, utility inconclusive, audio inconclusive too — `verdict.overall` becomes `TIE`/`BAD` from the walk itself) | — | **NOT COVERED** — verified by checking every fixture's `picks` block: every ungated fixture in the suite has `picks.naturalness` set to `"A"` or `"B"`, or (for `hierarchy_audio_decides`) resolves via the audio-decides branch instead. None reach this fallback. This is one of the nine branches `{EVAL-24}` requires; see the mechanical check below. |

## `{EVAL-24}` coverage threshold — mechanical check

Per `docs/EVAL_SPEC.md` §`{EVAL-24}`'s stated procedure: read every `Code |
Severity` row across `RULES_SPEC.md` §4.1-§4.8, filter to `Severity ==
error`; read the nine `{RULE-10}`..`{RULE-15}` branches above. For each,
confirm this file names a covering fixture id, not `NOT COVERED` and not a
silent omission.

**Error-severity codes: 12 total, filtered from the 34-code table below by
severity.** All 12 checked, all 12 covered:

| # | Code | Covering fixture |
|---|---|---|
| 1 | `SETUP_HEADPHONES` | `contradiction_preflight_and_turns` |
| 2 | `TURNS_BELOW_MIN` | `turns_short_and_mismatched` |
| 3 | `TURNS_MISMATCH` | `contradiction_preflight_and_turns` |
| 4 | `PROMPTS_NOT_EQUIVALENT` | `contradiction_preflight_and_turns` |
| 5 | `NOTES_MISSING` | `empty_state` |
| 6 | `PREMISE_ACCEPTED` | `ex3_owls` |
| 7 | `AUDIO_BOTH_GOOD_ILLEGAL` | `ex2_cutoff`, `contradiction_both_good_audio` |
| 8 | `AUDIO_PICK_CONTRADICTS` | `contradiction_audio_pick` |
| 9 | `UTILITY_PICK_CONTRADICTS` | `contradiction_utility_pick` |
| 10 | `OVERALL_PREFERS_GATED` | `contradiction_prefers_gated` |
| 11 | `DIMENSIONS_CONTRADICT` | `contradiction_dimensions_split` |
| 12 | `SUCCESS_FAIL_PREFERRED` | `contradiction_success_fail_preferred` |

**Threshold-gate / hierarchy-walk branches: 9 total.** 8 of 9 checked and
covered; **1 of 9 (`{RULE-15}` no-separating-evidence fallback) is `NOT
COVERED`** — see the branch table above for the verification method.

**Result: the `{EVAL-24}` gate is NOT MET.** All 12 in-scope error-severity
codes have a covering fixture — the six the lead listed
(`SETUP_HEADPHONES`, `TURNS_MISMATCH`, `PROMPTS_NOT_EQUIVALENT`,
`AUDIO_PICK_CONTRADICTS`, `UTILITY_PICK_CONTRADICTS`,
`SUCCESS_FAIL_PREFERRED`) are now closed by the five new fixtures. But
`{EVAL-24}`'s "must" set is error codes **and** branches, and one branch —
the Step 2 fallback that produces `verdict.overall in {"TIE","BAD"}` without
going through a threshold gate — has no fixture anywhere in the current
18-fixture suite. This is a real, previously-unreported gap, not a
restatement of one already known: the earlier "no worked example covers
TIE or BAD" note in `team_plan.md`'s Phase A gap list was about the trace
text (`{RULE-25}`, closed by T1 with a manual demonstration from T5, not a
fixture) — this is the first time the *branch itself* has been confirmed
uncovered by any golden fixture. Closing it needs one more adversarial
fixture (e.g. `picks: {naturalness: TIE, utility: TIE, audio: TIE, ...}`,
ungated, asserting `verdict.overall in {"TIE","BAD"}` and the `{RULE-25}`
tie-paragraph `draft_contains` substrings) — outside `T6-fixtures-required`'s
file ownership to author, reported here and to the lead rather than
actioned.

## `RULES_SPEC.md` section 4 finding-code coverage (34 codes)

### 4.1 Setup and consistency — conversation mode only (`{RULE-16}`)

| Code | Severity | Covering fixture | Status |
|---|---|---|---|
| `SETUP_HEADPHONES` | error | `contradiction_preflight_and_turns` | covered |
| `SETUP_PANNING` | warning | — | **NOT COVERED** (not required by `{EVAL-24}`) |
| `AUDIO_NOT_ISOLATED` | warning | — | **NOT COVERED** (not required) |
| `TURNS_BELOW_MIN` | error | `turns_short_and_mismatched` | covered (combined with mismatch fact, per `{EVAL-10}`) |
| `TURNS_MISMATCH` | error | `contradiction_preflight_and_turns` | covered (both sides clear 4 turns — 5 and 7 — with unequal counts, distinct from `turns_short_and_mismatched`'s below-floor case) |
| `TURNS_OK` | ok | `ex4_neighbour_prefer_a`, `ex4_neighbour_prefer_b`, `audit_exercise_charisma` | covered |
| `PROMPTS_NOT_EQUIVALENT` | error | `contradiction_preflight_and_turns` | covered |
| `PERSONA_NOT_HELD` | warning | — | **NOT COVERED** (not required) |
| `NO_INTERRUPTION_TEST` | info | — | **NOT COVERED** (not required) |

### 4.2 Evidence — both modes (`{RULE-17}`)

| Code | Severity | Covering fixture | Status |
|---|---|---|---|
| `NOTES_MISSING` | error | `empty_state` | covered |
| `NOTES_IMBALANCED` | warning | — | **NOT COVERED** (not required; checked programmatically — no fixture's `a.notes`/`b.notes` length pair satisfies `max>120 and min<0.35*max`, including the five new fixtures) |
| `EVIDENCE_MISSING` | warning | `empty_state` (structurally, both `a.best`/`b.best` empty) | fires, unasserted — not required by `{EVAL-24}` (warning severity) |
| `PROMPT_MISSING` | warning | `empty_state` (structurally, clips mode with `context.prompt` empty) | fires, unasserted, same reason; not required |
| `GROUND_TRUTH_MISSING` | info | — | **NOT COVERED** (not required; no `redteam`/`premise` fixture omits `ground_truth`; `ex3_owls` sets it) |

### 4.3 Scenario inversion (`{RULE-18}`)

| Code | Severity | Covering fixture | Status |
|---|---|---|---|
| `PUSHBACK_IS_SUCCESS` | ok | `ex3_owls` | covered |
| `PUSHBACK_PENALIZED` | warning | — | **NOT COVERED** (not required; needs a side with `premise_handling: pushback` that also carries a `threshold_utility` flag) |
| `PREMISE_ACCEPTED` | error | `ex3_owls` | covered |
| `PREMISE_HEDGED` | info | — | **NOT COVERED** (not required) |
| `PREMISE_UNRECORDED` | info | — | **NOT COVERED** (not required) |

### 4.4 Audio (`{RULE-19}`)

| Code | Severity | Covering fixture | Status |
|---|---|---|---|
| `AUDIO_BOTH_GOOD_ILLEGAL` | error | `ex2_cutoff`, `contradiction_both_good_audio` | covered |
| `AUDIO_PICK_CONTRADICTS` | error | `contradiction_audio_pick` | covered (`picks.audio: A`, `a.threshold_audio: [distortion]`, `b` clean; `picks.overall: B` so `OVERALL_PREFERS_GATED` stays silent and only the audio-pick contradiction is under test) |
| `AUDIO_SLIGHT_TOLERATED` | ok | `slight_noise_not_penalized` | covered |
| `AUDIO_BOTH_CLEAN` | info | `empty_state` (structurally: no audio flags, `picks.audio` unset/`None`) | fires, unasserted — not required by `{EVAL-24}` (info severity); condition requires `picks.audio is None`, which no fixture with an explicit `TIE` pick satisfies |

### 4.5 Utility (`{RULE-20}`)

| Code | Severity | Covering fixture | Status |
|---|---|---|---|
| `UTILITY_PICK_CONTRADICTS` | error | `contradiction_utility_pick` | covered (`picks.utility: A`, `a.threshold_utility: [instruction_failure]`, `b` clean; `picks.overall: B` so `OVERALL_PREFERS_GATED` stays silent) |

### 4.6 Overall coherence (`{RULE-21}`)

| Code | Severity | Covering fixture | Status |
|---|---|---|---|
| `OVERALL_PREFERS_GATED` | error | `contradiction_prefers_gated` | covered |
| `OVERALL_DIVERGES` | warning | `both_sides_breach` | covered |
| `OVERALL_COHERENT` | ok | `ex1_houseplant`, `ex2_cutoff`, `ex3_owls`, `ex4_neighbour_prefer_a`, `ex4_neighbour_prefer_b`, `audit_exercise_charisma`, `hierarchy_audio_decides` | covered |
| `DIMENSIONS_CONTRADICT` | error | `contradiction_dimensions_split` | covered |
| `HIERARCHY_REVERSED` | warning | `contradiction_dimensions_split` (asserted in `findings_include` as of T7's `cf986d8`) | covered; not required by `{EVAL-24}` but confirmed asserted, closing the "fires, unasserted" gap this file flagged in round 2 |
| `SUCCESS_FAIL_PREFERRED` | error | `contradiction_success_fail_preferred` | covered (`picks.overall: A`, `a.task_success: fail`, conversation mode, no threshold flags anywhere so nothing else contends for a finding) |
| `SUCCESS_PASS_WITH_THRESHOLD` | warning | — | **NOT COVERED** (not required; no fixture pairs `task_success: pass` with a `threshold_utility` flag on the same side — `contradiction_utility_pick` carries `threshold_utility` on `a` but does not set `a.task_success` at all) |

### 4.7 Error clusters (`{RULE-22}`)

| Code | Severity | Covering fixture | Status |
|---|---|---|---|
| `CLUSTERS_TO_REPORT` | info | `ex4_neighbour_prefer_a`, `ex4_neighbour_prefer_b`, `audit_exercise_charisma` | covered, including the per-side emission shape (one finding per qualifying side); not required by `{EVAL-24}` (info severity) |
| `PREFERRED_HAS_CLUSTERS` | warning | `ex4_neighbour_prefer_a`, `audit_exercise_charisma` (fires); `ex4_neighbour_prefer_b` (correctly excluded — B is preferred and carries no clusters) | covered in both directions; not required |

`{RULE-22.1}` (naturalness-scored entries excluded from `CLUSTERS_TO_REPORT`) is covered by `ex1_houseplant`'s explicit `findings_exclude: [CLUSTERS_TO_REPORT]` alongside `error_clusters: [over_structured]`.

### 4.8 Skip (`{RULE-23}`)

| Code | Severity | Covering fixture | Status |
|---|---|---|---|
| `TECHNICAL_SKIP` | warning | — | **NOT COVERED** (not required; no fixture sets `context.skip_reason`) |

## Summary of gaps

**In scope for `{EVAL-24}` (error codes and §3 branches) — one open item:**

- The `{RULE-15}` Step 2 "no-separating-evidence" fallback branch (naturalness `TIE`/`BAD`, utility and audio both inconclusive too, `verdict.overall` becomes `TIE`/`BAD` from the hierarchy walk itself, not a threshold gate). No fixture reaches it. This is the one thing standing between the suite and a met `{EVAL-24}` gate.

All 12 error-severity codes and the other 8 of 9 `{RULE-10}`..`{RULE-15}`
branches are covered as of this round; see the mechanical check above for
the full accounting.

**Out of scope for `{EVAL-24}` (warning/info/ok codes), recorded honestly
per `CLAUDE.md`'s coverage-manifest mandate, not required to close:**

- `SETUP_PANNING`, `AUDIO_NOT_ISOLATED`, `PERSONA_NOT_HELD`, `NO_INTERRUPTION_TEST` — every preflight field these need is left `true` in every conversation-mode fixture.
- `NOTES_IMBALANCED`, `GROUND_TRUTH_MISSING`.
- `PUSHBACK_PENALIZED`, `PREMISE_HEDGED`, `PREMISE_UNRECORDED`.
- `SUCCESS_PASS_WITH_THRESHOLD`.
- `TECHNICAL_SKIP`.
- Dimension-level `Pick.BAD` (as opposed to overall `Pick.BAD`, which `both_sides_breach` covers as a rater input — distinct from `verdict.overall == "BAD"` computed by the engine, which is the same gap as the in-scope fallback branch above).
- `repetitive`, `degradation`, `awkward_silence`, `speech_recognition` error clusters; `robotic_intonation` (clips-mode Naturalness evidence).
- `EVIDENCE_MISSING`, `PROMPT_MISSING`, `AUDIO_BOTH_CLEAN` fire inside `empty_state` but are not asserted by name.

None of these are silently assumed covered elsewhere in this document.
Closing the in-scope gap requires one new adversarial fixture; closing the
out-of-scope ones requires further fixtures or expanded `expect:` blocks —
both outside `T6-fixtures-required`'s file ownership (`ex1`..`ex4b`,
`audit_exercise_charisma`) to author, and are reported to
`T7-fixtures-adversarial` and the lead rather than actioned here.
