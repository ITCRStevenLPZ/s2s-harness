# Team Findings: Phase 3

Append discoveries immediately, after at most 2 search/read operations. Do not batch.

Format: `### [T-n] <short title>` then what you found, where (file:line or {RULE-n}), and what it implies for someone else's work.

---

### [lead] Reconnaissance corrections

- **`RULES_SPEC` section 4 defines 34 finding codes, not 29.** An earlier count of 29 that circulated in Wave 1 was wrong. By subsection: 4.1=9, 4.2=5, 4.3=5, 4.4=4, 4.5=1, 4.6=7, 4.7=2, 4.8=1.
- Section 4 tables carry columns `Code | Severity | Condition`, and for 4.1/4.3/4.6/4.7 also `Message gist`. There is **no label column anywhere**, yet `GRAPH_SPEC` section 1 defines `Finding.label`. Gap 4.
- `RULES_SPEC` section 7 invariants are tagged {RULE-40} through {RULE-45}, six of them. The trailing note in the spec explains why BUILD_PLAN once said seven.
- Section 3 states: "Each branch appends its own trace line. The trace is the user-facing explanation and is asserted on in the golden fixtures - treat the strings as part of the contract." But only the Step 1 gate cases 1, 2 and 4 have verbatim trace templates. Step 2 branches and case 3 ({RULE-12}) do not. Gaps 2 and 3.
- Section 6 scanner table lists **15 keys**. `speech_recognition` is in the section 1 catalogue but has no scanner row. The two tone signals {RULE-35} are described but have no patterns enumerated. Gap 6.
- `EVAL_SPEC` worked YAML uses `id: ex3_owls_false_premise`; its required-fixtures table lists `ex3_owls`. Unreconciled in the document.
- `RULES_SPEC` section 5 sentence 3 variant 1 contains a literal `gap(...)` with an unspelled ellipsis, unlike `evW` and `evL` which have exact fallback text. Gap 5.
- {RULE-25} TIE/BAD early return is described ("tie paragraph with a `gap()` asking what made them equivalent, plus a nudge to gather more evidence") but never quoted. No worked example covers a TIE or BAD verdict. Gap 1.

### [T3] normalize/decide built; three items still pending T1

- `rules/normalize.py` done: {RULE-5}..{RULE-9} implemented in the exact
  order the spec gives, idempotency-guarded so re-running it on an
  already-normalized side never double-appends `notable_noise` /
  `premise_redteam`.
- `rules/decide.py` done: all four Step 1 gate cases, `gate_name`, and the
  full six-branch Step 2 hierarchy walk are implemented per the spec's
  control flow (branch order, driver strings, `Verdict.overall` values
  are all verbatim, not provisional).
- Three trace-string items are placeholders, isolated so a later patch is
  a pure string substitution with zero control-flow change:
  1. {RULE-12} both-sides-breach trace (gap 3, already tracked).
  2. The five Step 2 (RULE-15) per-branch trace lines (gap 2, already
     tracked).
  3. **New, not in the original six-gap list:** RULES_SPEC section 3
     never defines the `{joined a.threshold_all}` list-join format used
     in the RULE-10/RULE-11 verbatim templates -- just the placeholder
     name. I implemented single-item as-is, two-item "X and Y", three-plus
     as an Oxford-comma list, isolated in `decide._join_english`. Flagging
     for T1 in case there is a project-specific convention I am missing
     (the draft's worked-example prose in EVAL_SPEC's ex2_cutoff paraphrases
     rather than using this literal join, so it is not directly evidence
     either way).
- None of the three pending items affect `Verdict.overall`, `.gated`, or
  `.gated_side` -- only `.trace`, which `audit`/`draft` do not read.
  T2-fixtures: hold off asserting exact trace text for Step 2 branches and
  the both-breach case until T1 broadcasts; the four RULE-10/11/13
  verbatim-template traces (single-breach and clean-gate cases) are safe
  to assert on now except for the exact join separator inside them.

### [lead] Carried over from Wave 1

- T2 of Wave 1 reported that `interrupts_user` ("interrupting me or talking over my turn") and `ignores_interruption` read awkwardly when spliced into `"{Side} had {display}"`. This was deliberately NOT fixed in Wave 1 because there was no rendered output to judge against. Phase 3 produces that output. T5-draft-scanner owns the observation: report it to T1-spec-gaps with the rendered sentence as evidence. Do not silently reword a spec display string.
- Wave 1 accepted a duplication-with-drift-test pattern: `Mode` and the catalogue key sets are declared in both `rules/catalog.py` and `models/state.py`, because `models/` may not import `rules/` under the ARCHITECTURE.md layer table. `tests/test_layering.py` asserts they stay identical. Do not "simplify" this by importing across the boundary.

### [T4] audit.py complete, 34/34 codes, two ambiguities resolved by literal reading

- Confirmed the 34-code count by subsection exactly matches the plan: 4.1=9, 4.2=5, 4.3=5, 4.4=4, 4.5=1, 4.6=7, 4.7=2, 4.8=1.
- **ASSUMPTION T2 MUST MATCH -- CLUSTERS_TO_REPORT / AUDIO_SLIGHT_TOLERATED are per-side.** Only 4.3's preamble literally says "For each side," but 4.4's and 4.7's rows use "a side has..." language for the same shape of check, and §4.3's explicit preamble is the closest textual anchor available, so the same reading was extended to those two codes. Implemented as: emit one finding per side that meets the condition (A before B), each carrying only that side's own list -- never one finding combining both sides. Lead confirmed (2026-07-26) this is consistent with §4.3 and should stand; a fixture must assert the per-side shape (e.g. two separate `CLUSTERS_TO_REPORT` findings when both sides carry reportable clusters, not one), not a combined-list shape. If T1's pending {RULE-43} ruling touches this while it's being resolved, follow T1's version instead.
- **SUPERSEDED by T1's ruling below ("[T1] {RULE-43} reconciled").** Original note: RULE-43 says "no flags and no picks", not "no notes"; a truly all-default `SideObservation` would still trip `NOTES_MISSING`. T1 ruled reading (2): {RULE-43} is scoped to the flag-derived/pick-derived codes only (section 4.4 Audio, 4.5 Utility, 4.6 Overall coherence); section 4.1/4.2's unconditional gates, `NOTES_MISSING` included, are supposed to fire on blank input, that is their purpose. No code change was needed in `audit.py` -- it already implemented exactly this scoping (section 4.4-4.6 checks all read `threshold_audio`/`threshold_utility`/`picks`/`verdict`, section 4.1/4.2 checks never gate on those). Re-verified on a truly empty state (blank `notes`/`best`, all defaults, no placeholder text): `NOTES_MISSING` fires as `error`, `EVIDENCE_MISSING` and `PROMPT_MISSING` fire as `warning`, and the only findings from section 4.4-4.6 are `AUDIO_BOTH_CLEAN` (info) and `OVERALL_COHERENT` (ok) -- zero errors among the 4.4-4.6 codes. `RULES_SPEC.md` is now 1.2.0.
- `TURNS_BELOW_MIN` treats `turns is None` as failing the 4-turn minimum (can't confirm the bar is cleared if it was never recorded), and is structured as an `if/elif/else` with `TURNS_MISMATCH`/`TURNS_OK` so exactly one of the three ever fires -- satisfies {EVAL-10}'s "one error, not two" by construction, not by a special case.
- `OVERALL_PREFERS_GATED` guards on `verdict.gated` (not just `picks.overall == verdict.gated_side`) because `Verdict.gated_side` defaults to `None` when ungated, and `picks.overall` is also `None` by default -- an unguarded `==` would have false-fired "prefers gated" on a state where nobody picked anything and nothing was gated.
- `Finding.label` was `""` for all 34 codes pending T1; T1's §4.9 {RULE-46} table (below) is now wired verbatim into `_LABELS` in `audit.py`. No other code changed.

---

### [T1] SendMessage unavailable in this session

Same finding T5 logged: the SendMessage tool is not present in my toolset. Broadcasting gap resolutions here instead, the moment each lands, per the "do not batch" rule. @T2-fixtures and @T3-normalize-decide and @T4-audit and @T5-draft-scanner: poll this file rather than waiting on a message.

### [T1] Gap 2 CLOSED — Step 2 hierarchy-walk trace strings (RULES_SPEC §3, still under `{RULE-15}`)

Added a "Step 2 trace templates" block right after the Step 2 pseudocode, one verbatim trace per branch: naturalness-decides, naturalness-None, utility-decides, audio-decides, and the no-separating-evidence fallback (with a conditional append distinguishing `BAD` vs `TIE`, mirroring the conditional-append style already used in `{RULE-10}`). No new ID: `{RULE-15}` already promised "each branch appends its own trace line" — this fills that promise, it does not add a new requirement. `{pick}` is a new placeholder convention documented inline, meaning "the full display of whichever side the branch names." Affects T2 (fixture `draft_contains`/trace assertions) and T3 (must literally emit these strings from `decide`). Read `docs/RULES_SPEC.md` §3 directly, do not paraphrase.

### [T1] Gap 3 CLOSED — both-sides-breach trace (RULES_SPEC §3, `{RULE-12}`)

Case `both > 0` now has a verbatim trace, structured like `{RULE-10}`'s (names both sides' specific `threshold_all` contents) but concluding "'Both Bad' is defensible on the affected dimensions" per the existing framing text, then falls through to Step 2 same as before. No new ID — `{RULE-12}` already existed and already said a trace gets appended; this supplies the missing wording. Affects T2 and T3.

---

### [T5] Blocked on T1 gaps 1, 5, 6 -- building everything else now

SendMessage is not available in this session, so flagging here instead of directly: I own `draft.py`/`scanner.py` and cannot finish without T1's resolution of:
- Gap 1 -- {RULE-25} TIE/BAD early-return paragraph, exact wording. Not cosmetic: {RULE-42} requires `build_draft` non-empty whenever `verdict.overall` is set, and TIE/BAD are members of `Pick`, so this paragraph is load-bearing, not optional polish.
- Gap 5 -- sentence 3 variant 1's third `gap(...)` (the one for `L.best` in the "gated, loser breached, Naturalness favoured the loser" case), exact placeholder text.
- Gap 6 -- `speech_recognition` scanner row and the two {RULE-35} tone-signal patterns.

Proceeding now with sentences 1, 2, 4, 5, 6, 7, 8 and the other 14 scanner rows, all fully specified. Will slot the three gaps in the moment T1 broadcasts, and will re-read this file and `team_progress.md` before finalizing. If T1 sees this before broadcasting, a direct note back here (or in `team_progress.md`) confirming exact strings, rather than me polling repeatedly, would help.

---

### [T1] Gaps 1, 5, 6 CLOSED — @T5-draft-scanner, these are yours, read `docs/RULES_SPEC.md` directly

**Gap 1 — `{RULE-25}` TIE/BAD paragraph.** Quoted in full now. `{outcome}` maps `TIE -> "Both Good"`, `BAD -> "Both Bad"` (the two non-A/B options in `CRIT-3`). Exact `gap()` inner text: `"name what specifically made the two sides feel equivalent here — the same strengths, or the same failure, on both"` — this satisfies "asking what made them equivalent" from the plan's description. The nudge covers both "extend the conversation" (conversation mode, phrased as "if this is a live exchange" so it reads naturally for clips mode too) and "relisten to both sides" (both modes), per the plan's "(extend the conversation / relisten)". No new ID — {RULE-25} already existed and already promised this paragraph.

**Gap 5 — `{RULE-28}` sentence 3 variant 1 gap text.** Spelled out as `gap("name the specific thing that made {L} seem more natural")`, matching the exact pattern of `evW`/`evL`'s `"name the specific thing that made {X} ___"` fallback. No new ID, same reasoning as above.

**Gap 6 — `{RULE-34}`/`{RULE-35}` scanner rows.** Added a `speech_recognition` row (16th row in the table, bilingual) rather than marking it unscannable — nothing distinguishes detecting it from the rater's notes from the other 15 clusters, so "unscannable" would have been an unjustified exception. Added a two-row sub-table under `{RULE-35}` for the tone signals (warmth/naturalness cue, possible slight room tone), both bilingual, both `kind="tone"` per `STATE-15`. No new IDs — both existing IDs already promised this content.

All six gaps plus the id discrepancy are now closed. Remaining for T1: Gap 4 (`Finding.label`, affects T2 + T4) and the `ex3_owls` id fix (affects T2), both next.

---

### [T3] CONFLICT flagged, not improvised: gap-2's `{pick}` vs `{RULE-41}` purity

@T1-spec-gaps @T2-fixtures: RULES_SPEC section 3's new Step 2 trace
templates define `{pick}` as "the full display of whichever side the
branch names (e.g. 'Model A' / 'Clip B')". That requires mode, which
`decide(a, b, picks) -> Verdict` does not receive as an argument and
`{RULE-41}` (same document, section 7) forbids it from reading anything
beyond `a.threshold_all`, `b.threshold_all` and `picks`. `decide` cannot
produce "Model A" / "Clip B" without either taking a mode/context
argument (breaking {RULE-41}) or a caller stitching mode in after the
fact (which contradicts "each branch appends its own trace line" being
something `decide` itself does).

Per CLAUDE.md's standing instruction ("when a rule appears to conflict
with the task, stop and say so ... underspecification is a spec bug"),
I am not silently picking the "full display" reading. Resolution taken
for this deliverable, pending T1 ratification: `decide()` emits the bare
side letter ("A" / "B") everywhere `{A}`/`{B}`/`{pick}` appears in a Step
1 or Step 2 trace line, preserving {RULE-41} exactly. If T1 rules that
mode-aware display is actually required in the trace, that display
substitution has to happen in a layer that receives `TaskContext` --
`nodes/` (state assembly) or `draft.py` post-processing the trace before
it reaches the rater -- not inside `decide` itself, and `{RULE-41}`'s
wording would need a carve-out for that. `rules/decide.py` implements
the bare-letter form now; the four RULE-10/RULE-11/RULE-12/RULE-13
Step-1 traces and all five Step-2 traces are otherwise byte-exact
transcriptions of T1's verbatim templates. T2: assert on "A"/"B" for now;
if T1 rules the other way this is a one-function patch in
`decide._display for trace` (currently there isn't one -- bare letters
are used directly), not a control-flow change.

---

### [T1] Gap 4 CLOSED — @T4-audit and @T2-fixtures, `Finding.label` (RULES_SPEC new §4.9, new `{RULE-46}`)

New ID, unlike the other five gaps: no existing `§4.x` ID covered a label column, so this is genuinely new normative content per the plan's own instruction, not a fill-in. Added `§4.9 Finding labels` right after `§4.8 Skip`, a `Code | Label` table covering all 34 codes. Labels group by subsection *topic*, not mechanically by the existing `4.1`-`4.8` numbering, because `4.6 Overall coherence` mixes three unrelated concerns (overall-pick coherence, dimension/hierarchy contradiction, task-success contradiction) that should not share one chip. Groupings: `SETUP` (headphones/panning/isolation), `TURNS`, `PROMPTS`, `PERSONA`, `TESTING` (interruption-test-not-done), `EVIDENCE` (all of §4.2), `PREMISE` (all of §4.3), `AUDIO` (all of §4.4 — matches the literal example in `GRAPH_SPEC`), `UTILITY` (§4.5), `OVERALL` (the three `OVERALL_*` codes), `HIERARCHY` (`DIMENSIONS_CONTRADICT`, `HIERARCHY_REVERSED`), `SUCCESS` (the two `SUCCESS_*` codes), `CLUSTERS` (§4.7), `SKIP` (§4.8). This is my reconstruction, not recovered intent — GRAPH_SPEC gave one example and no other guidance, so any short category grouping is defensible; flagging per the plan's instruction to note reconstructed text. @T4-audit: read the new §4.9 table directly rather than re-deriving groupings, so `audit.py` and this spec cannot drift.

### [T1] id discrepancy CLOSED — @T2-fixtures, `ex3` fixture id

`EVAL_SPEC.md`'s worked YAML now reads `id: ex3_owls` (was `ex3_owls_false_premise`), matching the required-fixtures table. Chose the table's short form since every other row in that table is short and thematic and does not restate `scenario_type` (already `premise` in the fixture body). No assertion changed. Name your fixture file `tests/golden/ex3_owls.yaml`.

**Phase A complete.** All six gaps plus the id discrepancy closed in `docs/RULES_SPEC.md` (now 1.1.0) and `docs/EVAL_SPEC.md` (now 1.1.0). New IDs added: `{RULE-46}` only (Finding labels) — every other resolution filled text an existing ID already promised, per the plan's own instruction not to legislate new behavior. No criteria, hierarchy, threshold, cluster-list, audio-tolerance or scenario-inversion text was touched; both files stayed inside my file ownership (`docs/RULES_SPEC.md`, `docs/EVAL_SPEC.md`).

---

### [T1] Gap 7 (new, surfaced by T3) CLOSED — `joined()` list-join format, new `{RULE-47}`

@T3-normalize-decide, @T2-fixtures: your flag was correct, `{joined a.threshold_all}` was used in `{RULE-10}`/`{RULE-11}`/`{RULE-12}`/`{RULE-26}` but never defined. Added a `joined(list)` definition to §3, right after the `thr_a`/`thr_b` line, before Step 1: renders each key's `Display` string from §1 (not the raw key), one item as itself, two as `"X and Y"`, three-plus as an Oxford-comma list `"X, Y, and Z"`. This matches T3's own placeholder implementation (`decide._join_english`) exactly, so no code change should be needed on T3's side beyond confirming the match — please diff and confirm. New ID `{RULE-47}` because no existing ID covered a formatting helper (this is a different kind of gap than the other six, which were all missing trace/paragraph *text*; this one was a missing *function definition*). Read `docs/RULES_SPEC.md` §3 directly. All Step 1 and Step 2 trace templates, and Sentence 1 in §5, now have every placeholder they use fully defined — nothing else in the traces or sentences is undefined that I can find, but keep flagging if you hit another one.

---

### [T4] Report to team-lead (SendMessage unavailable, same as T1/T5) -- audit.py complete

Committed and pushed at `021233c` (aea9211..021233c on origin/main), `src/s2s_harness/rules/audit.py` only, never `git add -A`.

**Diff summary.** New file implementing `audit(state, verdict) -> list[Finding]` per RULES_SPEC section 4 in full: all 34 codes across 4.1-4.8 (`{RULE-16}`..`{RULE-23}`), plus `{RULE-46}` labels wired from T1's section 4.9 delivery mid-build. One private function per subsection, called in spec table order from `audit()`, then `sorted()` by severity (error/warning/info/ok) with Python's stable sort so within-tier order is exactly append order. `_LABELS` is the verbatim Code|Label table from section 4.9.

**Rationale.** Read RULES_SPEC section 4 in full plus EVAL_SPEC before writing anything. Verified the 34-code count programmatically (regex over the file: 34 distinct `_finding(` call codes, matching 9/5/5/4/1/7/2/1). Two judgment calls beyond a literal table read, both already logged above under "[T4] audit.py complete, 34/34 codes": per-side CLUSTERS_TO_REPORT/AUDIO_SLIGHT_TOLERATED, and RULE-43's "notes/best populated, only flags/picks empty" reading.

**Invariant proof, real runs against T3's `normalize`/`decide`, no mocking:**
- RULE-43 (populated notes/best, all flags+picks empty) -> only `AUDIO_BOTH_CLEAN`(info) and `OVERALL_COHERENT`(ok). Zero errors.
- RULE-45 case 1 (redteam, B pushback, no other flags on B) -> `PREMISE_ACCEPTED`(error, side A only), `PUSHBACK_IS_SUCCESS`(ok), `OVERALL_COHERENT`(ok). Zero negative findings mention Clip B.
- RULE-45 case 2 (B pushback + rater also flagged `threshold_utility` on B) -> adds `PUSHBACK_PENALIZED`(warning) exactly as documented ("aimed at the rater... not a penalty on the model"); `PUSHBACK_IS_SUCCESS`(ok) still present.

**Quality gates.** `uv run ruff check src/s2s_harness/rules/audit.py` -> All checks passed. `uv run mypy src/s2s_harness/rules/audit.py` -> Success: no issues found in 1 source file. `graphify update .` -> 560 nodes, 648 edges, 48 communities (re-run after wiring T1's label table).

**Cosmetic note.** My commit message picked up a stray trailing "EOF )" from a heredoc-quoting slip on my end (visible via `git log -1`). The diff/code is correct, only the message tail is malformed. Not amended or force-pushed, per the no-amend policy -- flagging rather than silently fixing.

No open blockers on my side. Not aware of any teammate depending on me as a dependency.

**Update after lead review:** pushed a comment-only follow-up at `c51ff7c` (021233c..c51ff7c) documenting the `turns is None` -> below-min inference in `TURNS_BELOW_MIN` as non-spec judgment text, per the lead's note that it should be explicit so nobody "fixes" it later without checking fixture impact. No logic changed; ruff/mypy re-verified clean. Also strengthened the CLUSTERS_TO_REPORT/AUDIO_SLIGHT_TOLERATED per-side note above into an explicit "assumption T2 must match" per the lead's confirmation that reading stands. `audit.py` is otherwise untouched and waiting on T1's {RULE-43}-vs-`NOTES_MISSING` ruling before any further change -- will implement exactly what T1 rules, not before.

---

### [T1] CONFLICT RESOLVED — @T3-normalize-decide's `{pick}` vs `{RULE-41}` purity

@T3-normalize-decide: correctly caught, correctly not improvised past — this is exactly the "stop and say so" case. Ruling: your bare-letter resolution was right, ratified and now written into the spec, not just accepted in code. Added a "Trace side-references" paragraph to §3 (right after the new `joined()` note, before Step 1): `{A}`, `{B}` and `{pick}` in every trace string render as the bare side letter `"A"`/`"B"`, never a mode-aware form, because `decide(a, b, picks)` has no `TaskContext` argument and `{RULE-41}` restricts it to `(a.threshold_all, b.threshold_all, picks)`. This is stated to apply retroactively to `{A}`/`{B}` in `{RULE-10}`/`{RULE-11}`/`{RULE-12}` too, which were ambiguous on this point before now — not just to the new §RULE-15 templates. Also corrected my own Gap-2 `{pick}` definition line, which had wrongly said "full display... e.g. 'Model A'" — that was my error, now fixed to match this ruling. Mode-aware display ("Model A" / "Clip B") is explicitly assigned to `draft.py` (§5, which already owns the `Model`/`Clip` vocabulary rule) or a UI/node rendering layer, never to `decide`. No new `{RULE-n}` — this is a clarification of `{RULE-10}`/`{RULE-11}`/`{RULE-12}`/`{RULE-15}`/`{RULE-41}` resolving their mutual ambiguity, not new behavior. @T2-fixtures: assert bare `"A"`/`"B"` in any trace-content assertion, not `"Model A"`/`"Clip B"`.

---

### [T1] CONFLICT RESOLVED — @T2-fixtures @T4-audit — `{RULE-43}` vs `NOTES_MISSING`, RULES_SPEC/EVAL_SPEC now 1.2.0

`T4-audit` caught a real one, not a gap: {RULE-43} said "a state with no flags and no picks produces zero error findings," unqualified, but `NOTES_MISSING` (§4.2, error) fires on any default `SideObservation` because its `notes` field is empty by default — true regardless of flags or picks. Two readings, weighed in a reconciliation note now in `RULES_SPEC.md` §7 (below the invariant list, same pattern `criteria/project-criteria.md` uses for its own turns-count conflict):

1. **Rejected** — treat {RULE-43} as presupposing populated notes (T4's placeholder-notes demonstration). This is defensible in isolation but it would force `EVAL-12`'s `empty_state` fixture to not actually be empty to pass, which is a bad test: that fixture exists specifically to prove the engine survives the truly blank state the bridge's debounced `POST /evaluate` produces before a rater types anything.
2. **Adopted** — {RULE-43} is scoped to flag-derived and pick-derived findings only: the codes in §4.4 Audio, §4.5 Utility and §4.6 Overall coherence, whose conditions read `threshold_audio`/`threshold_utility`/`picks`/`verdict`. §4.1/§4.2's unconditional setup and evidence gates, `NOTES_MISSING` chief among them, are unaffected and are *supposed* to fire on blank input — that is the invariant's actual purpose: guard against flag/pick-reading logic misfiring or raising on `None`/default values (e.g. `OVERALL_COHERENT` comparing `None == None`), not a claim that an empty submission should look clean.

This stays a spec-internal engineering clarification, not a criteria change — nothing in `criteria/project-criteria.md` speaks to finding counts on blank input — so I did not escalate to the lead as a criteria question. No new `{RULE-n}`, same reasoning as the `{pick}`/`{RULE-41}` fix: narrowing an existing invariant's wording to resolve an internal contradiction, not adding behavior.

**@T2-fixtures:** updated `EVAL-12`'s row in `EVAL_SPEC.md` to say explicitly — `NOTES_MISSING` (and any other §4.1/§4.2 gate the fixture's mode triggers) belongs in `findings_include` for `empty_state`, not `findings_exclude`. Write the fixture genuinely empty (default `SideObservation`, no flags, no picks); do not add placeholder notes to dodge the error.

**@T4-audit:** your `audit.py` reading (populated notes/best) was reasonable given the unqualified original text, but per this ruling `audit.py` needs no code change at all — `NOTES_MISSING` firing on truly empty state is now the documented-correct behavior, not something to suppress. Please re-verify your RULE-43 demonstration against a *genuinely* empty `SideObservation` (no notes) and confirm `NOTES_MISSING` fires as the sole error, rather than keeping the placeholder-notes version as the canonical proof.

Both files bumped to 1.2.0 (from 1.1.0) with a "Wave 2, second pass" note at the top of each.

---

### [T6] Took over the required-fixtures half of stalled T2-fixtures; all six already existed and check out

Found on arrival: `tests/golden/ex1_houseplant.yaml`, `ex2_cutoff.yaml`,
`ex3_owls.yaml`, `ex4_neighbour_prefer_a.yaml`, `ex4_neighbour_prefer_b.yaml`,
`audit_exercise_charisma.yaml` already written on disk (uncommitted), plus
T7's harness (`_golden_lib.py`, `test_golden.py`) and all seven adversarial
fixtures, also uncommitted. Rather than assume correctness, verified every
`expect:` value in my six files by hand against `docs/RULES_SPEC.md` section
3/5 templates and `criteria/worked-examples.md`, sentence by sentence
(§3 Step 1/Step 2 trace branch selection, §5 sentences 1/2/3/4/7/8, `frag()`
splicing, `joined()` single-item behavior) -- not by running the engine
first. All six check out exactly against the templates; no edits were
needed. `uv run pytest tests/golden tests/test_layering.py` -> 15 passed
(13 fixtures + 2 layering tests; `test_determinism.py` not yet built by T7).

### [T6] `contradiction_dimensions_split` (T7's fixture) appears to under-assert `HIERARCHY_REVERSED`

Not my file, not edited. `{RULE-21}`'s `HIERARCHY_REVERSED` condition
(`picks.overall in {"A","B"}`, `picks.naturalness == other_side`,
`not verdict.gated`) reads as satisfied by this fixture's own state
(`picks.overall: A`, `picks.naturalness: B`, ungated) at the same time as
the `DIMENSIONS_CONTRADICT` condition it does assert. Its `expect:` block
lists `DIMENSIONS_CONTRADICT` in `findings_include` but says nothing about
`HIERARCHY_REVERSED` either way. Flagging for @T7-fixtures-adversarial to
add `HIERARCHY_REVERSED` to `findings_include` if this reading is right, or
to correct my reading if it's wrong -- not touching the file myself, it is
outside `T6`'s ownership. Logged in `tests/golden/COVERAGE.md` as "fires,
unasserted" rather than silently treating it as covered.

### [T6] `tests/golden/COVERAGE.md` written

Reconciles all 13 fixtures against `criteria/project-criteria.md` `{CRIT-1}`
through `{CRIT-11}` and against all 34 `RULES_SPEC.md` section 4 finding
codes. Honest gaps recorded rather than a false-complete matrix per
CLAUDE.md: 18 of 34 codes have no covering fixture at all (every
conversation-mode preflight-failure code, `TURNS_MISMATCH`,
`NOTES_IMBALANCED`, `GROUND_TRUTH_MISSING`, `PUSHBACK_PENALIZED`,
`PREMISE_HEDGED`, `PREMISE_UNRECORDED`, `AUDIO_PICK_CONTRADICTS`,
`UTILITY_PICK_CONTRADICTS`, `SUCCESS_FAIL_PREFERRED`,
`SUCCESS_PASS_WITH_THRESHOLD`, `TECHNICAL_SKIP`), 3 more fire inside
`empty_state`/`contradiction_dimensions_split` but are not asserted by name
(`EVIDENCE_MISSING`, `PROMPT_MISSING`, `AUDIO_BOTH_CLEAN`, plus the
`HIERARCHY_REVERSED` item above), and the Step-2 "Audio decides" hierarchy
branch has no fixture at all. None of these are within `T6`'s six owned
files to fix (they would require new adversarial fixtures or edits to T7's
existing ones), so they are reported rather than actioned. `{CRIT-11}`
(final review) and part of `{CRIT-10}` ("As an AI..." framing) are marked
N/A -- rater-side self-checks with no corresponding `{RULE-n}` finding code,
confirmed by reading section 4's full code list, not assumed.

---

### [T6] Lead caught a real COVERAGE.md drift; audited all 45 claims, fixed the one wrong one

Lead's review found `COVERAGE.md`'s `{CRIT-4}` row claiming `ex2_cutoff`
covers `clicks` when the fixture only flagged `cutoff` -- a real defect,
not a false positive. Root cause: `criteria/worked-examples.md` Example 2
says Clip B "cuts off abruptly and has a small pop," and the fixture's
`b.worst`/`b.notes` prose already carried the pop, but `b.threshold_audio`
never did, so the fixture under-represented its own source example and the
coverage claim was aspirational rather than true.

Fixed: `ex2_cutoff.yaml`'s `b.threshold_audio` is now `[cutoff, clicks]`.
Sentence 1's `draft_contains` string was re-derived BY HAND from
`RULES_SPEC.md` section 3's `joined()` two-item format ({RULE-47}) --
"audio cut off mid-word and audible clicks or pops" -- using each key's
Display string from section 1, before ever running the suite, per the
anti-drift rule. `uv run pytest tests/golden/test_golden.py -k ex2_cutoff`
then passed against that hand-derived string on the first run: this is the
expected outcome of a correct derivation matching a correct engine, not a
case of adjusting the fixture to the engine's output.

Then audited every other cell in `COVERAGE.md` against the actual fixture
files rather than trusting the matrix as written: read every `error_clusters`
/ `threshold_utility` / `threshold_audio` / `background_noise` /
`premise_handling` / `task_success` / `turns` / `preflight` / `picks` value
across all 13 fixtures directly (grep + a small script for the
`NOTES_IMBALANCED` length-ratio condition, which is not eyeball-checkable),
and cross-checked the "NOT COVERED" claims by confirming the relevant flag
combination is genuinely absent everywhere, not just absent from the
fixtures I expected to check. 45 distinct claims audited (11 `{CRIT-n}`
clause-row claims + 34 finding-code rows). Two things worth noting, one
wrong, one merely unclear:
- **Wrong (fixed):** the `ex2_cutoff` `clicks` cell, above.
- **Unclear (reworded, not wrong):** the `{CRIT-4}` `ex3_owls` cell said
  "`false_premise` via `premise_redteam`," which could be misread as the
  raw `false_premise` catalogue key being present. It never is in that
  fixture -- only the derived `premise_redteam` key fires. Reworded to say
  so explicitly and added the raw `false_premise` key to the gap list,
  since no fixture sets it directly (every premise/redteam fixture goes
  through the `accepted` -> `premise_redteam` derivation path, never a
  hand-set `false_premise` flag).

Everything else in the 45-claim audit held up against the files as written
(see the audit log now appended to the top of `COVERAGE.md` for the full
account). `uv run pytest tests/ -q` -> 39 passed, 1 skipped (the
`nodes/polish.py` exemption in `test_token_boundary.py`, correctly skipped
since that file does not exist yet), on the tree including T7's
`cf986d8` fix. Committed and pushed at `6e23500` (`cf986d8..6e23500`),
scoped to `tests/golden/ex2_cutoff.yaml` and `tests/golden/COVERAGE.md`
only.

---

### [T6] COVERAGE.md reconciled with T7's five EVAL-24 fixtures; one real branch gap found

The lead flagged that `COVERAGE.md` (last touched at `6e23500`) still
denied coverage for six error codes T7's `a95e3dd`/`b0aa7fd`
(`contradiction_preflight_and_turns`, `contradiction_audio_pick`,
`contradiction_utility_pick`, `contradiction_success_fail_preferred`,
`hierarchy_audio_decides`, `EVAL-19`..`EVAL-23`) had already closed --
the mirror image of the earlier `clicks` drift, this time denying
coverage that exists rather than claiming coverage that doesn't. Read all
five fixture files directly rather than trusting names or the lead's list.

Updated every affected row (4.1's `SETUP_HEADPHONES`/`TURNS_MISMATCH`/
`PROMPTS_NOT_EQUIVALENT`, 4.4's `AUDIO_PICK_CONTRADICTS`, 4.5's
`UTILITY_PICK_CONTRADICTS`, 4.6's `SUCCESS_FAIL_PREFERRED`), the `{CRIT-2}`/
`{CRIT-3}`/`{CRIT-4}`/`{CRIT-8}` clause rows, and confirmed T7's `cf986d8`
`HIERARCHY_REVERSED` fix landed (now `covered`, not `fires, unasserted`).

Then ran `{EVAL-24}`'s mechanical check in full for the first time: 12
error-severity codes in `RULES_SPEC.md` §4 (filtered from all 34 by
severity), all 12 now covered. 9 threshold-gate/hierarchy-walk branches in
§3 (`{RULE-10}`/`{RULE-11}`/`{RULE-12}`/`{RULE-13}` plus the five `{RULE-15}`
Step 2 branches), 8 of 9 covered. **The ninth -- the Step 2
"no-separating-evidence" fallback, where `verdict.overall` becomes
`TIE`/`BAD` from the hierarchy walk itself rather than a threshold gate --
has no covering fixture anywhere in the 18-fixture suite.** Verified this
by checking every fixture's `picks` block by hand: every ungated fixture
either sets `picks.naturalness` to `"A"`/`"B"`, or (only `hierarchy_audio_decides`)
resolves via the audio-decides branch; none leave naturalness, utility and
audio all inconclusive simultaneously. This is a new finding, not a
restatement of the old "no worked example covers TIE/BAD" trace-text gap
(that one was about `{RULE-25}`'s wording, closed by T1 with a manual
demonstration, not a fixture) -- this is the branch itself, confirmed
uncovered by any golden fixture, and it means **`{EVAL-24}`'s gate is NOT
MET** even though all 12 in-scope error codes now pass. Reported plainly in
`COVERAGE.md`'s new mechanical-check section rather than fudged. Closing it
needs one more adversarial fixture (all three dimension picks inconclusive,
ungated, asserting `verdict.overall in {"TIE","BAD"}` and the `{RULE-25}`
tie-paragraph text) -- outside my file ownership to author; flagged to
T7-fixtures-adversarial and the lead.

`uv run pytest tests/ -q` -> 49 passed, 1 skipped, unchanged (this was a
documentation-only fix, no fixture behavior changed). `graphify update .`
-> 712 nodes, 999 edges, 52 communities. Committed and pushed
`tests/golden/COVERAGE.md` only at `e617b6e` (`149c39f..e617b6e`).

---

### [T6] EVAL-24 gate now MET: hierarchy_no_separating_evidence closes the last branch gap

Wrote `tests/golden/hierarchy_no_separating_evidence.yaml`: `picks:
{naturalness: TIE, utility: TIE, audio: TIE}`, neither side gated, so
`{RULE-15}`'s Step 2 walk runs out of rungs and reaches the fallback
(`verdict.overall == "TIE"`, `driver == "No separating evidence"`). Chose
the `TIE` arm over `BAD` because both clips are genuinely comparable with
no failure on either side -- "Both Bad" would not have been the honest
read of the scenario, and `{EVAL-24}` only requires the branch be reached,
not both of its internal outcomes (recorded as a non-blocking nuance in
`COVERAGE.md` rather than silently treated as fully exhausted).

This is also the first fixture in the suite to exercise `{RULE-25}`'s
TIE/BAD early-return paragraph. Transcribed the exact wording from
`RULES_SPEC.md` 1.2.0 section 5 by hand -- *"Neither {A} nor {B} comes out
clearly ahead on this pass, so the vote stands as '{outcome}.' {gap(...)}
Before finalizing, extend the conversation a turn or two if this is a live
exchange, or relisten to both sides once more, in case a differentiator
was missed."* -- substituting `{A}`/`{B}` = "Clip A"/"Clip B" (mode-aware,
draft.py's own vocabulary rule, clips mode chosen) and `{outcome}` = "Both
Good" (naturalness TIE per `{RULE-25}`'s own mapping), before ever running
the suite. It passed against that hand-derived string on the first run --
`uv run pytest tests/golden/test_golden.py -k hierarchy_no_separating_evidence`
green immediately, which is the expected outcome of a correct derivation
meeting a correct engine, not evidence of running the engine first.

`docs/EVAL_SPEC.md` was orphaned (`T1-spec-gaps` terminated) so I added the
new `EVAL-25` required-fixture row directly, additively, bumped to 1.4.0
with a one-line version note, per the lead's explicit instruction. That
commit also carries T1's prior uncommitted 1.3.0 work (the `{EVAL-24}`
section and `EVAL-19`..`EVAL-23` rows), which had never been committed on
its own -- my 1.4.0 edit sat on top of it in the same working tree, so both
land together in one commit, called out explicitly in the commit message
per the lead's note that this is expected.

Updated `COVERAGE.md` throughout: the section 3 branch table's last row
flips to `covered`; the `{EVAL-24}` mechanical check section now reports
**9/9 branches and 12/12 error codes covered, gate MET**; the "Summary of
gaps" in-scope list is now empty (zero open items), with the untested
`BAD` arm of the fallback noted honestly as a non-blocking nuance, not
folded silently into "covered."

`uv run lint` / `uv run mypy` / `uv run pytest tests/ -q` all green (51
passed, 1 skipped -- unchanged skip is the `nodes/polish.py` exemption).
`graphify update .` -> 713 nodes, 1000 edges, 52 communities. Committed
and pushed `tests/golden/hierarchy_no_separating_evidence.yaml`,
`tests/golden/COVERAGE.md` and `docs/EVAL_SPEC.md` at `506aca9`
(`e617b6e..506aca9`).

---

### [T4] Re-verified against RULES_SPEC 1.2.0's {RULE-43} scoping — no code change needed

Re-ran the demonstration on a genuinely empty `SideObservation` (no `notes`, no `best`, every field at its default), `TaskContext(mode="clips")`, empty `Picks()`:

```
error   NOTES_MISSING            EVIDENCE
warning EVIDENCE_MISSING         EVIDENCE
warning PROMPT_MISSING           EVIDENCE
info    AUDIO_BOTH_CLEAN         AUDIO
ok      OVERALL_COHERENT         OVERALL

all error codes: ['NOTES_MISSING']
```

`NOTES_MISSING` is the sole error, exactly as the ruling describes. Zero errors among the §4.4-4.6 (flag/pick-derived) codes — checked programmatically against the full set of §4.4-4.6 error codes (`AUDIO_BOTH_GOOD_ILLEGAL`, `AUDIO_PICK_CONTRADICTS`, `UTILITY_PICK_CONTRADICTS`, `OVERALL_PREFERS_GATED`, `DIMENSIONS_CONTRADICT`, `SUCCESS_FAIL_PREFERRED`), none present. `audit.py` already implemented this scoping without knowing it — every §4.4-4.6 check reads `threshold_audio`/`threshold_utility`/`picks`/`verdict`, never `notes`/`best`, and every §4.1/§4.2 check is unconditional on flags/picks — so no diff was needed, and none was made. My earlier placeholder-notes demonstration is superseded; this is the canonical one. T2: `NOTES_MISSING`, `EVIDENCE_MISSING` and `PROMPT_MISSING` (clips mode) all belong in `findings_include` for a genuinely-empty `empty_state` fixture, per T1's note above.

---

### [T5] draft.py + scanner.py complete; carry-over splice finding confirmed with rendered evidence

Both modules implemented against RULES_SPEC 1.1.0/1.2.0 section 5/6 (section 5/6 text unchanged by the 1.2.0 RULE-43 bump, confirmed by reading the diff before starting). Every sentence slot ({RULE-24}..{RULE-33}) and every scanner rule ({RULE-34}..{RULE-39}) is implemented, all three of my blocking gaps (1, 5, 6) consumed verbatim from T1's Wave 2 closure.

**Carry-over finding, now with rendered output (Wave 1 left this open pending exactly this):** rendering sentence 4 ({RULE-29}) for a side carrying `interrupts_user` and `ignores_interruption` produces:

> "I am flagging the following: Model A showed an embodied-experience claim, interrupting me or talking over my turn, and ignoring my attempts to interrupt or correct it."

`"{Side} showed {display}"` is grammatical for `an embodied-experience claim` (a noun phrase) but reads awkwardly for the other two, which are bare gerund clauses ("interrupting me...", "ignoring my attempts...") -- "Model A showed interrupting me" is not natural English, unlike "Model A showed an embodied-experience claim." This confirms `rules/catalog.py`'s own splice-verdict comment (T2, Wave 1) that these two entries fail the `"{Side} had {display}"`-style splice test. Per my task's instruction, not silently rewording the catalogue's display strings or `RULES_SPEC.md` section 1 -- reporting here for `T1-spec-gaps`/`criteria-keeper` review. A fix (if wanted) would live in `criteria/project-criteria.md` and the catalogue's display strings, e.g. rephrasing to noun-phrase form ("repeated interruptions of my turns" / "ignoring my attempts to interrupt or correct it" -> "a failure to yield when I tried to interrupt or correct it"), not in `draft.py`'s sentence templates, which are otherwise verbatim from the spec.

**{RULE-42} proof (TIE):** `build_draft` on a `Verdict(overall="TIE", ...)` returns non-empty:
> "Neither Model A nor Model B comes out clearly ahead on this pass, so the vote stands as 'Both Good.' 【name what specifically made the two sides feel equivalent here — the same strengths, or the same failure, on both】 Before finalizing, extend the conversation a turn or two if this is a live exchange, or relisten to both sides once more, in case a differentiator was missed."

Same non-empty result confirmed for `BAD` ("Both Bad").

**{RULE-32} no-re-listing proof, ex2_cutoff-equivalent (B gated on Audio Quality, cutoff+clicks):**
> "I prefer Clip A overall because Clip B has a clear issue that crosses the project's threshold — audio cut off mid-word and audible clicks or pops — and a side with that kind of problem should not be preferred while the other one is clean. Under the project hierarchy of Naturalness / Engagement over Utility over Audio Quality, the threshold requirement on Audio Quality matters most here because naturalness only carries its full weight once both sides clear the minimum bar for accuracy and audio, and here one of them does not. Clip A showed this — warm, unhurried delivery — while Clip B was weaker: cuts off mid-word at the end and includes an audible pop. On Audio Quality I penalized accordingly: Clip B: audio cut off mid-word and audible clicks or pops, so 'Both Good' is not appropriate here. Beyond that, I observed no other threshold-level issues in either clip. Therefore, Clip A is the stronger fit for the project's North Star."

Sentence 7 says "Beyond that, I observed no other threshold-level issues in either clip" and does not re-list "audio cut off mid-word" or "audible clicks or pops" a second time -- both already named in sentence 1 -- confirming the trap `{EVAL-2}` tests for is handled.

**ex3_owls draft_contains proof** (EVAL_SPEC's literal fixture, built and run against real `normalize`/`decide`, not mocked): `"I prefer Clip B overall"`, `"cannot outweigh a threshold failure"`, and `"counts as a success, not a refusal to help"` all present verbatim; zero `【` in the rendered draft (every fixture field was populated) -- matches `draft_excludes: ["【"]`.

**Determinism:** `build_draft` run 50x on an identical `EvaluationState`/`Verdict` (including one with `interrupts_user`/`ignores_interruption`/`embodied` clusters) produced byte-identical output every time.

**Quality gates:** `uv run ruff check src/s2s_harness/rules/draft.py src/s2s_harness/rules/scanner.py` -> All checks passed. `uv run mypy` (full project run per `pyproject.toml`'s `files = ["src", "scripts"]`) -> Success: no issues found in 13 source files.

No open blockers on my side. Not aware of any teammate depending on me as a dependency; `nodes/draft.py`/`nodes/scanner.py` (not yet built) will be the callers.

---

### [T7] Took over the adversarial-fixtures half of stalled T7; found the prior instance had already finished, just never committed or reported

On arrival, all seven adversarial fixtures, `tests/golden/_golden_lib.py` (the
shared runner) and `tests/golden/test_golden.py` already existed on disk,
uncommitted, correct on inspection, and passing (`uv run test-golden` -> 13
passed even before I touched anything). `tests/test_determinism.py` and
`tests/test_token_boundary.py` did not exist yet -- that was the actual gap.
Verified the pre-existing work rather than assuming it: traced
`contradiction_both_good_audio`, `contradiction_prefers_gated`,
`contradiction_both_good_audio`'s `AUDIO_BOTH_GOOD_ILLEGAL` condition and
`contradiction_prefers_gated`'s `OVERALL_PREFERS_GATED` condition by hand
against `rules/audit.py`'s and `rules/decide.py`'s actual branch logic (not
by running them and copying output -- by reading the condition and computing
what it evaluates to on the fixture's literal input), confirmed both match.

**Real gap found and fixed, not the engine's fault:** T6 had already flagged
(above, "[T6] `contradiction_dimensions_split` (T7's fixture) appears to
under-assert `HIERARCHY_REVERSED`") that `RULE-21`'s `HIERARCHY_REVERSED`
condition is also true of `contradiction_dimensions_split`'s state
(`picks.naturalness == other_side` alongside `DIMENSIONS_CONTRADICT`'s own
condition) and was previously unasserted. Confirmed T6's reading against
`audit.py`'s `_overall_coherence` directly, added `HIERARCHY_REVERSED` to
that fixture's `findings_include`, re-ran, green. This was a fixture gap
(under-assertion), not an engine bug and not a spec bug -- no engine or spec
file touched.

I did not build a competing `tests/conftest.py` with duplicate
fixture-loading logic once I found `_golden_lib.py` already did the job
correctly (I had drafted one before discovering it; deleted it rather than
ship two divergent implementations of the same pipeline, which is exactly
the drift risk the team-lead's message warned about for T6). Fixed a stale
ownership attribution in `_golden_lib.py`'s docstring (said "Owned by
T2-fixtures", predates this wave's roster) to `T7-fixtures-adversarial`,
no logic changed.

**New work, both reusing existing logic rather than re-implementing:**
- `tests/test_determinism.py` ({EVAL-15}): every fixture, 50 runs, asserts
  `Verdict.model_dump()` / `[Finding.model_dump(), ...]` / draft string are
  byte-identical run to run. Imports `_golden_lib.run_fixture` directly --
  same pipeline `test_golden.py` exercises, not a second one.
- `tests/test_token_boundary.py` ({EVAL-16}): imports `check_file` /
  `SRC_ROOT` / `SANCTIONED_RELATIVE_PATH` from
  `scripts/token_boundary_check.py` rather than re-walking the AST a second
  way, per that script's own docstring calling this file its "authoritative
  pytest version." Parametrized per source file for a readable failure
  message per offending file, plus one test proving the `nodes/polish.py`
  exemption actually skips (currently `SKIPPED`, file does not exist yet --
  Phase 4).

**Full suite, from repo root:** `uv run test-golden` -> 13 passed. `uv run
pytest tests/ -v` -> 40 collected, 39 passed, 1 skipped (the polish.py
exemption test, correctly skipped, not failed, since `nodes/polish.py`
doesn't exist yet). `uv run ruff check tests/... ` and `uv run mypy
tests/test_determinism.py tests/test_token_boundary.py` both clean. `uv run
lint` (whole repo) found ONE pre-existing formatting issue, in
`src/s2s_harness/rules/audit.py` (T4's file, not mine, not touched) -- three
long string-literal lines `ruff format` would wrap differently. Flagging for
T4/T1 review, not fixed by me.

Committed and pushed, scoped to my files only (never `git add -A`):
`f8febda` (seven fixtures + `_golden_lib.py` + `test_golden.py` +
`test_determinism.py` + `test_token_boundary.py` + `graphify-out/`), then
`cf986d8` (the `HIERARCHY_REVERSED` fixture fix + `graphify-out/`). Did not
stage or commit `tests/golden/ex2_cutoff.yaml`, which I observed change
under me mid-session (T6 actively editing live) -- not my file.

---

### [T1] User ruled on the coverage-honesty question — @T7-fixtures-adversarial @T6-fixtures-required, `EVAL_SPEC.md` now 1.3.0

New task from the lead, not a gap in the original six: `CLAUDE.md` claimed Tier 1 covers "100% of rules-engine branches"; `T6`'s honest `COVERAGE.md` showed 24 of 34 codes not fully covered. The user rejected both "make it literally 100%" and "leave the false claim" and ruled a stated, checkable bar instead. `CLAUDE.md`'s Two-tier test gate line is already updated by the lead (operator-managed, not touched by me) to: *"Covers every error-severity finding code and every threshold and hierarchy branch per `tests/golden/COVERAGE.md`; info and ok severity codes are out of scope."* `EVAL_SPEC.md` now states this as a normative requirement, new `## Coverage threshold {EVAL-24}`, mirroring `CLAUDE.md`'s wording so the two documents cannot drift on what "covers" means. Scope, spelled out: every **error-severity** code in RULES_SPEC §4, plus the four Step 1 gate cases and five Step 2 branches in §3. `warning`/`info`/`ok` codes are not required — not because of a special carve-out, but because the "must" set was only ever defined as error-severity codes plus branches; `warning` was never in it, same as `info`/`ok`. `COVERAGE.md` should keep tracking `warning` honestly regardless, per `CLAUDE.md`'s separate coverage-manifest mandate — just not gated on it.

**@T7-fixtures-adversarial — five new rows added to the Adversarial fixtures table, yours to author, id and one-line spec each:**
- `contradiction_preflight_and_turns` — `EVAL-19` — conversation mode, `SETUP_HEADPHONES` + `PROMPTS_NOT_EQUIVALENT` + `TURNS_MISMATCH` together (three independent conditions, safe to combine per the lead's instruction: no shared field, no interaction). Turns must both clear 4 but differ (e.g. 5/6) to hit `TURNS_MISMATCH` rather than `turns_short_and_mismatched`'s `TURNS_BELOW_MIN` combined-fact branch. Leave every other preflight field `true`.
- `contradiction_audio_pick` — `EVAL-20` — `picks.audio` names the side carrying `threshold_audio` while the other is clean.
- `contradiction_utility_pick` — `EVAL-21` — `picks.utility` names the side carrying `threshold_utility` while the other is clean.
- `contradiction_success_fail_preferred` — `EVAL-22` — conversation mode, `picks.overall` names a side marked `task_success: fail`.
- `hierarchy_audio_decides` — `EVAL-23` — closes the one hierarchy gap `COVERAGE.md` found: `picks.naturalness: TIE`, `picks.utility: TIE`, neither side gated, `picks.audio` decides; asserts `verdict.driver == "Audio Quality"` and `verdict.overall` matches `picks.audio`. This is the `{RULE-15}` Step-2 audio-decides trace template T1 wrote earlier in the wave — use it verbatim in `draft_contains`/trace assertions if you assert on trace text.

Kept `AUDIO_PICK_CONTRADICTS` and `UTILITY_PICK_CONTRADICTS` as separate fixtures rather than combining them — combining would require one side to carry both an audio and a utility breach or two sides each breaching a different dimension, which would trip the Step 1 threshold gate (both-breach case) and conflate this test with `both_sides_breach`'s scenario. The lead's "combine where independent" instruction was scoped to the §4.1 preflight codes specifically; I read it as not extending to these two.

**@T6-fixtures-required:** `COVERAGE.md` needs the five new fixture rows added to the inventory table and the six now-closing codes (`SETUP_HEADPHONES`, `TURNS_MISMATCH`, `PROMPTS_NOT_EQUIVALENT`, `AUDIO_PICK_CONTRADICTS`, `UTILITY_PICK_CONTRADICTS`, `SUCCESS_FAIL_PREFERRED`) plus the Step-2 audio-decides hierarchy-branch row moved from **NOT COVERED** to covered once T7's fixtures land — not before. Also worth a top-of-file note recording the new `{EVAL-24}` coverage-threshold definition, since it changes what "gap" means for every remaining `warning`-severity **NOT COVERED** row (still worth recording honestly, just no longer gates the merge).

`docs/EVAL_SPEC.md` bumped 1.2.0 -> 1.3.0. `docs/RULES_SPEC.md` untouched this pass — no rule text changed, only which fixtures must exist. `criteria/` untouched. `CLAUDE.md` untouched by me, per the lead's explicit instruction.

---

### [T1] Filename reconciliation needed — @T7-fixtures-adversarial, please confirm or correct

The lead has told T7 to author these five fixtures with descriptive filenames without waiting on my ids. I wrote `docs/EVAL_SPEC.md`'s Adversarial fixtures table using my own proposed names (`contradiction_preflight_and_turns`, `contradiction_audio_pick`, `contradiction_utility_pick`, `contradiction_success_fail_preferred`, `hierarchy_audio_decides`), matching the one-fixture-per-contradiction convention the existing seven already use. If T7 picked different names, post them here and I will update the `id` column to match T7's actual filenames rather than the other way around — the spec row should describe the fixture that exists, not the reverse. `EVAL-19` through `EVAL-23` stay attached to whichever five rows close these seven gaps (`SETUP_HEADPHONES`, `PROMPTS_NOT_EQUIVALENT`, `TURNS_MISMATCH`, `AUDIO_PICK_CONTRADICTS`, `UTILITY_PICK_CONTRADICTS`, `SUCCESS_FAIL_PREFERRED`, Step-2 audio-decides) regardless of what the files end up called; the ids track the gaps closed, not the strings I guessed.

---

### [T7] Status report to lead, plus the five coverage-threshold fixtures landed and renamed to T1's ids

**Status the lead asked about, as of this check:** by the time this message
was read, `tests/test_determinism.py` and `tests/test_token_boundary.py`
already existed and all seven adversarial fixtures plus `_golden_lib.py`
were already committed and pushed at `f8febda`, with the
`HIERARCHY_REVERSED` under-assertion fix at `cf986d8` (see my earlier
"[T7] Took over..." entry above for the full diff summary and gate output).
The lead's status check crossed in transit with that work landing — nothing
outstanding from the original assignment.

**New assignment, done:** authored all five coverage-threshold fixtures
before finding T1's broadcast (used provisional `EVAL-19`..`EVAL-23` ids and
my own descriptive filenames, exactly per the lead's "use T1's ids rather
than inventing your own, watch for the broadcast" instruction — provisional
because the broadcast had not landed yet when I started). Every `expect:`
value derived from `docs/RULES_SPEC.md` v1.2.0's literal condition tables
and `rules/catalog.py`'s Display strings (`distortion` -> "distortion or
robotic artifacts", `instruction_failure` -> "failure to follow the
instruction"), read directly, never from running `decide`/`audit`/`draft`
and copying output. Verified independence of `SETUP_HEADPHONES` /
`TURNS_MISMATCH` / `PROMPTS_NOT_EQUIVALENT` against `audit.py`'s
`_setup_and_consistency` before combining them into one fixture (no
early-return or shared-field interaction between the three).

**Found T1's broadcast immediately after** (`EVAL_SPEC.md` 1.3.0, new
`{EVAL-24}` coverage-threshold requirement) — T1's proposed filenames
(`contradiction_preflight_and_turns`, `contradiction_audio_pick`,
`contradiction_utility_pick`, `contradiction_success_fail_preferred`,
`hierarchy_audio_decides`) matched what I had already built in substance;
renamed the four that did not match my working filenames via `git mv`,
updated each `id:` field and header comment to cite the ratified id instead
of "provisional," no test content or `expect:` value touched. `T1`: no
further reconciliation needed on my end, your proposed names are now the
actual filenames.

**Suite state, both commits:** `uv run pytest tests/ -q` -> 49 passed, 1
skipped (the `nodes/polish.py` exemption, correctly skipped) both before and
after the rename. `uv run ruff check tests` clean. `graphify update .` run
after each change.

Committed and pushed, scoped to my files only: `a95e3dd` (five new fixtures
+ `graphify-out/`), then `b0aa7fd` (the four renames to T1's ids +
`hierarchy_audio_decides.yaml`'s comment update + `graphify-out/`). Did not
stage `docs/EVAL_SPEC.md`, which I observed change live under me mid-session
(T1 actively editing) — not my file.

**@T6-fixtures-required:** the six now-closed codes and the Step-2
audio-decides hierarchy branch are ready for `COVERAGE.md`'s inventory table
and NOT COVERED rows to move to covered, per T1's note above — five new
fixture files exist on disk at `tests/golden/{contradiction_preflight_and_turns,
contradiction_audio_pick,contradiction_utility_pick,
contradiction_success_fail_preferred,hierarchy_audio_decides}.yaml`, ids
`EVAL-19`..`EVAL-23`.

---

### [T7] Answering lead's two messages: attribution confirm, wording correction, audit.py fix

**Attribution, confirmed:** yes, `tests/test_determinism.py` and
`tests/test_token_boundary.py` are mine, committed at `f8febda` along with
the seven original adversarial fixtures and `_golden_lib.py`/`test_golden.py`.
The rename commit the lead saw as "staged renames still in flight" was
already committed and pushed at `b0aa7fd` by the time that message arrived
(crossed in transit, same as the earlier status check) -- `git log` on my
end shows `b0aa7fd` as an ancestor of current `HEAD`, nothing left staged.

**Wording correction, taken:** the lead is right that "verified against
`rules/audit.py`" and "derived from RULES_SPEC and copied `audit.py`'s
output" read identically in a summary line even though only the first
happened. What I actually did, precisely: read `RULES_SPEC.md`'s condition
tables and `rules/catalog.py`'s `Display` strings to compute the expected
`Finding` codes and draft substrings by hand, then separately opened
`audit.py`/`decide.py` to confirm my hand-computed reading of the *condition
logic* matched what was implemented (the same kind of check T6 did on the
six required fixtures, described there as "verified by hand ... not by
running the engine"). That is reading source to confirm a condition, not
deriving an expectation from output -- but I will use "verified against
RULES_SPEC section N" going forward per the lead's instruction, since that
is the unambiguous phrasing and the distinction should not depend on a
reader trusting my intent.

**`rules/audit.py` lint fix, done:** `ruff format src/s2s_harness/rules/audit.py`
(three implicit string concatenations near `SETUP_PANNING`/`PROMPT_MISSING`/
`OVERALL_COHERENT` that `ruff format --check` wanted on single lines,
mechanical only, no message text or condition changed). `uv run lint`,
`uv run mypy`, and `uv run pytest tests/ -q` (49 passed, 1 skipped) all
re-verified clean after. Committed separately from the fixture rename per
the lead's instruction, at `149c39f`, scoped to `src/s2s_harness/rules/audit.py`
and `graphify-out/` only.

**@T6-fixtures-required:** already flagged above (my prior entry) that the
six now-closed error codes plus the Step-2 audio-decides branch are ready
for `COVERAGE.md`; repeating the ping here since this entry is more likely
to be the last thing you read before picking it up.

---
