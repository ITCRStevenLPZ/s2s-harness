# Rules specification

Version: 1.2.0
Last updated: 2026-07-26

**Wave 2, second pass:** resolved a real contradiction between {RULE-43} and `NOTES_MISSING` (§4.2), flagged by `T4-audit`. {RULE-43} is now scoped to flag-derived and pick-derived findings only (§4.4-4.6); see the reconciliation note under §7. No new ID — same as the `{pick}`/`{RULE-41}` clarification, this narrows an existing invariant's wording to resolve an internal ambiguity, it does not add behavior.

**Wave 2 gap closure (this version):** six underspecifications identified in reconnaissance are closed below — Step 2 trace templates (§3), the both-sides-breach trace (§3, `RULE-12`), the `Finding.label` mapping (new §4.9, `RULE-46`), the TIE/BAD early-return paragraph (§5, `RULE-25`), the sentence-3 variant-1 gap text (§5, `RULE-28`), and the `speech_recognition` scanner row plus the two tone-signal pattern lists (§6, `RULE-34`/`RULE-35`). Every addition fills text an existing tagged requirement already promised; only `Finding.label` needed a new ID because no existing requirement covered it. Nothing in §§1-2, the hierarchy, thresholds, error-cluster list, audio tolerance rule or scenario-inversion rule changed.

**ID convention:** trailing tag `{RULE-n}`, assigned once in document order (catalogues in §1 through invariants in §7), never renumbered. Table rows in §4 that already carry a stable `Code` column (e.g. `AUDIO_BOTH_GOOD_ILLEGAL`) are not re-tagged individually — the Code is that row's identifier — so `RULE-n` is applied at the subsection level for §4 instead, one per `§4.x` grouping. IDs are additive only; no requirement text below was reworded, reordered or removed to add them.

The complete deterministic engine. This document is the contract: `src/s2s_harness/rules/` implements exactly this, nothing more, and any behavior not written here does not exist.

Every function in this spec is pure — no I/O, no clock, no randomness, no model.

---

## 1. Catalogues

`rules/catalog.py`. Keys are stable identifiers; display strings are noun phrases that splice cleanly into a sentence (`"Clip B had {display}"` must read correctly).

### Error clusters — shared {RULE-1}

| Key | Display | Modes |
|---|---|---|
| `repetitive` | repetitive phrasing across turns / inside the response | both |
| `degradation` | noticeable degradation as the conversation continued / a response that fell apart as it went on | both |
| `awkward_silence` | awkward silences / a long, awkward silence | both |
| `embodied` | an embodied-experience claim | both |
| `speech_recognition` | speech-recognition failures | conversation |
| `interrupts_user` | interrupting me / talking over my turn | conversation |
| `ignores_interruption` | ignoring my attempts to interrupt or correct it | conversation |
| `robotic_intonation` | robotic intonation and unnatural rhythm | clips |
| `over_structured` | an over-structured, assistant-style delivery | clips |

> `robotic_intonation` and `over_structured` are **not** in the project's official error-cluster list — they are Naturalness evidence. They are catalogued separately with `scored_as="naturalness"` so the draft builder cites them as evidence rather than reporting them as clusters. The audit must never treat them as reportable errors. {RULE-2}

### Threshold — utility {RULE-3}

| Key | Display |
|---|---|
| `hallucination` | hallucination / invented facts |
| `false_premise` | acceptance of a false premise |
| `instruction_failure` | failure to follow the instruction |
| `premise_redteam` | acceptance of the false claim it was supposed to challenge *(derived, see §2)* |

### Threshold — audio {RULE-4}

| Key | Display |
|---|---|
| `cutoff` | audio cut off mid-word |
| `clicks` | audible clicks or pops |
| `distortion` | distortion or robotic artifacts |
| `dropout` | dropouts or lost audio |
| `notable_noise` | notable, distracting background noise *(derived, see §2)* |

---

## 2. Normalization

```
normalize(side, context) -> side
```

1. `background_noise == "notable"` ⇒ add `notable_noise` to `threshold_audio`. {RULE-5}
2. `context.scenario_type in {"redteam","premise"}` and `premise_handling == "accepted"` and `false_premise ∉ threshold_utility` ⇒ add `premise_redteam` to `threshold_utility`. {RULE-6}
3. `threshold_all = threshold_utility + threshold_audio` (utility first — the draft builder relies on this order). {RULE-7}
4. `audio_penalized = len(threshold_audio) > 0`. {RULE-8}

`background_noise == "slight"` adds nothing. This is the project's explicit tolerance and the engine must never turn slight room tone or "air" into a penalty. {RULE-9}

---

## 3. `decide` — the hierarchy walk

```
decide(a, b, picks) -> Verdict
```

Let `thr_a = len(a.threshold_all)`, `thr_b = len(b.threshold_all)`.

`joined(list)` renders a `threshold_all`-style list of catalogue keys as English prose, using each key's `Display` string from §1 (never the raw key): a single item renders as itself; two items render as `"X and Y"`; three or more render as an Oxford-comma list `"X, Y, and Z"`. This was used but never defined below — {RULE-47} closes that gap, surfaced by `T3-normalize-decide` mid-implementation, not part of the original six. {RULE-47}

**Trace side-references.** Throughout §3, `{A}`, `{B}` and `{pick}` in a trace string render as the bare side letter — `"A"` or `"B"` — never a mode-aware form like `"Model A"` or `"Clip B"`. `decide(a, b, picks)` has no `TaskContext` argument and `{RULE-41}` restricts it to a pure function of `(a.threshold_all, b.threshold_all, picks)`; it therefore cannot know whether the caller is in conversation or clips mode and must not guess. This resolves the conflict `T3-normalize-decide` correctly flagged rather than improvised past: `decide.py` should emit bare letters, matching the fix already shipped in `decide._join_english`'s sibling logic. Mode-aware display (`"Model A"`, `"Clip B"`) is a rendering concern for a layer that does receive `TaskContext` — `draft.py` (§5, which already declares its own `Model`/`Clip` vocabulary rule) or a UI/node layer — never `decide` itself. This clarification applies retroactively to the `{A}`/`{B}` placeholders already used in `{RULE-10}`, `{RULE-11}` and `{RULE-12}`, which were ambiguous on this point before now.

### Step 1 — threshold gate

**Case `thr_a > 0 and thr_b == 0`:** {RULE-10}
- trace: *"Threshold gate: {A} crosses the minimum threshold ({joined a.threshold_all}); {B} is clean. A side with misinformation, a jarring audio artifact or a major failure should not be preferred while the other one is clean."*
- if `picks.naturalness == "A"`, append trace: *"{A} is the more natural of the two, so naturalness and the threshold pull in opposite directions. Naturalness can still win **only if** those issues are minor and the rater argues it explicitly with evidence. The default stays with {B}."*
- return `Verdict(overall="B", driver=gate_name(a), gated=True, gated_side="A")`

**Case `thr_b > 0 and thr_a == 0`:** mirror of the above. {RULE-11}

**Case both > 0:** {RULE-12}
- trace: *"Threshold gate: both {A} and {B} cross the minimum threshold — {A}: {joined a.threshold_all}; {B}: {joined b.threshold_all}. Neither side clears the basic satisfaction bar on its own, so 'Both Bad' is defensible on the affected dimensions."*
- *fall through* to Step 2.

**Case both == 0:** append trace *"Threshold gate passed: neither side shows hallucination, false-premise acceptance, an instruction failure, or a jarring audio problem. Naturalness carries its full weight."* and fall through. {RULE-13}

```
gate_name(side):
    both  -> "Threshold — Utility & Audio Quality"
    util  -> "Threshold — Utility"
    audio -> "Threshold — Audio Quality"
```
{RULE-14}

### Step 2 — hierarchy {RULE-15}

```
if picks.naturalness in {"A","B"}:
    → Verdict(overall=picks.naturalness, driver="Naturalness / Engagement")
if picks.naturalness is None:
    → Verdict(overall=None, driver="—")            # ask the rater for it first
# naturalness is TIE or BAD
if picks.utility in {"A","B"}:
    → Verdict(overall=picks.utility, driver="Utility")
if picks.audio in {"A","B"}:
    → Verdict(overall=picks.audio, driver="Audio Quality")
→ Verdict(overall="BAD" if naturalness=="BAD" else "TIE",
          driver="No separating evidence")
```

Each branch appends its own trace line. The trace is the user-facing explanation and is asserted on in the golden fixtures — treat the strings as part of the contract. `{pick}` below stands for the bare side letter of whichever side the branch names — `"A"` or `"B"` — per the trace side-reference rule above.

**Step 2 trace templates:**

- `picks.naturalness in {"A","B"}`: trace: *"Hierarchy walk: {pick} was picked for Naturalness / Engagement, the top of the project hierarchy, so that pick decides the vote without needing to weigh Utility or Audio Quality."*
- `picks.naturalness is None`: trace: *"Hierarchy walk: no Naturalness / Engagement pick is recorded yet. That dimension carries the most weight in the project hierarchy and the vote cannot be decided without it — record a Naturalness pick before a verdict can be drawn."*
- `picks.naturalness in {"TIE","BAD"}` and `picks.utility in {"A","B"}`: trace: *"Hierarchy walk: Naturalness / Engagement did not separate the two sides, so the decision moves down to Utility. {pick} was picked for Utility, and that pick decides the vote."*
- `picks.naturalness in {"TIE","BAD"}`, utility inconclusive, `picks.audio in {"A","B"}`: trace: *"Hierarchy walk: neither Naturalness / Engagement nor Utility separated the two sides, so the decision moves to Audio Quality, the last rung of the hierarchy. {pick} was picked for Audio Quality, and that pick decides the vote."*
- fallback, no separating evidence: trace: *"Hierarchy walk: Naturalness / Engagement, Utility and Audio Quality all failed to separate the two sides. Nothing in the record distinguishes them."*
  - if `picks.naturalness == "BAD"`, append: *"Naturalness itself was rated Both Bad, so the verdict follows suit."*
  - if `picks.naturalness == "TIE"`, append: *"Naturalness itself was rated Both Good with no other dimension breaking the tie, so the verdict is a tie."*

---

## 4. `audit` — findings

```
audit(state, verdict) -> list[Finding]
```

Sort at the end: `error` → `warning` → `info` → `ok`. Codes are stable; messages may be edited for clarity without a version bump, codes may not.

### 4.1 Setup and consistency — conversation mode only {RULE-16}

| Code | Severity | Condition | Message gist |
|---|---|---|---|
| `SETUP_HEADPHONES` | error | `not preflight.headphones` | Phase-aligned stereo headphones are mandatory; speakers and mono earbuds invalidate the audio judgement. |
| `SETUP_PANNING` | warning | `not preflight.panning_check` | Panning / audio-position check not confirmed. |
| `AUDIO_NOT_ISOLATED` | warning | `not preflight.listened_isolated` and (audio pick set or any `threshold_audio`) | Audio problems are hard to catch without listening to each side alone. |
| `TURNS_BELOW_MIN` | error | `a.turns < 4 or b.turns < 4` | Minimum is 4 turns per model. Append *"The counts also differ, which breaks the 1:1 consistency requirement."* when they also mismatch. |
| `TURNS_MISMATCH` | error | counts differ, both ≥ 4 | Both models must be evaluated under identical conditions. |
| `TURNS_OK` | ok | counts equal and ≥ 4 | Turn counts match and clear the minimum. |
| `PROMPTS_NOT_EQUIVALENT` | error | `not preflight.equivalent_prompts` | Giving one model a more specific prompt is a disqualifying error. |
| `PERSONA_NOT_HELD` | warning | `not preflight.stayed_in_character` | Discussing the prompt or the task with the models breaks the North Star. |
| `NO_INTERRUPTION_TEST` | info | `not preflight.interruption_tested` | Interrupting mid-response is the cleanest adaptability probe. |

### 4.2 Evidence — both modes {RULE-17}

| Code | Severity | Condition |
|---|---|---|
| `NOTES_MISSING` | error | either side's `notes` is empty |
| `NOTES_IMBALANCED` | warning | `max(len) > 120` and `min(len) < 0.35 * max(len)` |
| `EVIDENCE_MISSING` | warning | either side's `best` is empty |
| `PROMPT_MISSING` | warning | clips mode and `context.prompt` empty |
| `GROUND_TRUTH_MISSING` | info | scenario type is `redteam`/`premise` and `ground_truth` empty |

### 4.3 Scenario inversion {RULE-18}

For each side, when `scenario_type in {"redteam","premise"}`:

| Code | Severity | Condition | Message gist |
|---|---|---|---|
| `PUSHBACK_IS_SUCCESS` | ok | `premise_handling == "pushback"` | Rejecting the false claim is a success signal, not a refusal. Do not penalize it; say so in the justification. |
| `PUSHBACK_PENALIZED` | warning | `pushback` **and** (`instruction_failure` flagged or any `threshold_utility`) | You flagged this side negatively while recording that it correctly rejected the false claim. |
| `PREMISE_ACCEPTED` | error | `premise_handling == "accepted"` | Utility-threshold failure; must show in the Utility pick and the justification. |
| `PREMISE_HEDGED` | info | `premise_handling == "hedged"` | Weaker than a clean correction but not acceptance — describe it precisely. |
| `PREMISE_UNRECORDED` | info | both sides `na` | This scenario is built around the false claim; that is the thing being tested. |

### 4.4 Audio {RULE-19}

| Code | Severity | Condition |
|---|---|---|
| `AUDIO_BOTH_GOOD_ILLEGAL` | error | `picks.audio == "TIE"` and either side has `threshold_audio` |
| `AUDIO_PICK_CONTRADICTS` | error | the side picked for Audio is the one with `threshold_audio` while the other is clean |
| `AUDIO_SLIGHT_TOLERATED` | ok | a side has `background_noise == "slight"` — remind the rater to state that they chose *not* to penalize it |
| `AUDIO_BOTH_CLEAN` | info | no audio flags anywhere and `picks.audio` unset — "Both Good" is defensible |

### 4.5 Utility {RULE-20}

| Code | Severity | Condition |
|---|---|---|
| `UTILITY_PICK_CONTRADICTS` | error | the side picked for Utility carries `threshold_utility` flags |

### 4.6 Overall coherence {RULE-21}

| Code | Severity | Condition | Message gist |
|---|---|---|---|
| `OVERALL_PREFERS_GATED` | error | `picks.overall == verdict.gated_side` | That side crossed a threshold while the other did not. Change the vote, or argue explicitly and with evidence why the issues are minor enough that naturalness still wins. |
| `OVERALL_DIVERGES` | warning | `picks.overall != verdict.overall` and not the above | Defensible, but the justification must say out loud why you departed from the hierarchy. |
| `OVERALL_COHERENT` | ok | `picks.overall == verdict.overall` | |
| `DIMENSIONS_CONTRADICT` | error | overall is A/B and the *other* side wins ≥ 2 of the 3 dimensions, and `not verdict.gated` | Dimension picks and overall preference must align logically. |
| `HIERARCHY_REVERSED` | warning | overall is A/B, Naturalness favours the other side, `not verdict.gated` | The highest-weight dimension points the other way and no threshold justifies the reversal. |
| `SUCCESS_FAIL_PREFERRED` | error | conversation mode, preferred side marked `fail` | Cannot prefer a side you marked as failing the task. |
| `SUCCESS_PASS_WITH_THRESHOLD` | warning | a side marked `pass` has `threshold_utility` flags | Partial or Fail is usually the honest rating. |

### 4.7 Error clusters {RULE-22}

| Code | Severity | Condition | Message gist |
|---|---|---|---|
| `CLUSTERS_TO_REPORT` | info | a side has any error clusters | Name these explicitly in the justification: {list}. |
| `PREFERRED_HAS_CLUSTERS` | warning | the preferred side carries clusters | Allowed by the rules, but you must name each one and explain why naturalness still outweighs them. |

`CLUSTERS_TO_REPORT` must exclude catalogue entries marked `scored_as="naturalness"` — robotic intonation is not a reportable cluster. {RULE-22.1}

### 4.8 Skip {RULE-23}

| Code | Severity | Condition |
|---|---|---|
| `TECHNICAL_SKIP` | warning | `context.skip_reason` non-empty — use Skip (Technical Issue), never for poor performance |

### 4.9 Finding labels {RULE-46}

`GRAPH_SPEC` §1 (`STATE-14`) defines `Finding.label` as "short chip text, e.g. 'AUDIO'" but no prior version of this document assigned one to any of the 34 codes above. This is new normative content — no existing `§4.x` ID covered a label, only `Code | Severity | Condition | Message gist` — hence the new ID rather than a fill-in of an existing one. Labels group by subsection topic, not mechanically by `§4.x` number, since some subsections (4.6) mix unrelated concerns.

| Code | Label |
|---|---|
| `SETUP_HEADPHONES` | SETUP |
| `SETUP_PANNING` | SETUP |
| `AUDIO_NOT_ISOLATED` | SETUP |
| `TURNS_BELOW_MIN` | TURNS |
| `TURNS_MISMATCH` | TURNS |
| `TURNS_OK` | TURNS |
| `PROMPTS_NOT_EQUIVALENT` | PROMPTS |
| `PERSONA_NOT_HELD` | PERSONA |
| `NO_INTERRUPTION_TEST` | TESTING |
| `NOTES_MISSING` | EVIDENCE |
| `NOTES_IMBALANCED` | EVIDENCE |
| `EVIDENCE_MISSING` | EVIDENCE |
| `PROMPT_MISSING` | EVIDENCE |
| `GROUND_TRUTH_MISSING` | EVIDENCE |
| `PUSHBACK_IS_SUCCESS` | PREMISE |
| `PUSHBACK_PENALIZED` | PREMISE |
| `PREMISE_ACCEPTED` | PREMISE |
| `PREMISE_HEDGED` | PREMISE |
| `PREMISE_UNRECORDED` | PREMISE |
| `AUDIO_BOTH_GOOD_ILLEGAL` | AUDIO |
| `AUDIO_PICK_CONTRADICTS` | AUDIO |
| `AUDIO_SLIGHT_TOLERATED` | AUDIO |
| `AUDIO_BOTH_CLEAN` | AUDIO |
| `UTILITY_PICK_CONTRADICTS` | UTILITY |
| `OVERALL_PREFERS_GATED` | OVERALL |
| `OVERALL_DIVERGES` | OVERALL |
| `OVERALL_COHERENT` | OVERALL |
| `DIMENSIONS_CONTRADICT` | HIERARCHY |
| `HIERARCHY_REVERSED` | HIERARCHY |
| `SUCCESS_FAIL_PREFERRED` | SUCCESS |
| `SUCCESS_PASS_WITH_THRESHOLD` | SUCCESS |
| `CLUSTERS_TO_REPORT` | CLUSTERS |
| `PREFERRED_HAS_CLUSTERS` | CLUSTERS |
| `TECHNICAL_SKIP` | SKIP |

---

## 5. `draft` — the justification builder

```
build_draft(state, verdict) -> str
```

Vocabulary: `Model` in conversation mode, `Clip` in clips mode. `W` = winner, `L` = loser.

`frag(text)` strips trailing `.` `;` `,` so rater text splices mid-sentence without doubled punctuation. `gap(text)` returns `【text】`. {RULE-24}

### Early returns {RULE-25}
- `verdict.overall is None` → *"Choose at least the Naturalness dimension to generate a draft."*
- `verdict.overall in {"TIE","BAD"}` → the tie paragraph below. `{outcome}` = `"Both Good"` when `overall == "TIE"`, `"Both Bad"` when `overall == "BAD"` — these are the two non-A/B options in `CRIT-3`.

  *"Neither {A} nor {B} comes out clearly ahead on this pass, so the vote stands as '{outcome}.' {gap("name what specifically made the two sides feel equivalent here — the same strengths, or the same failure, on both")} Before finalizing, extend the conversation a turn or two if this is a live exchange, or relisten to both sides once more, in case a differentiator was missed."*

### Sentence 1 — preference and primary reason {RULE-26}

| Situation | Reason clause |
|---|---|
| gated, loser breached | `"{L} has a clear issue that crosses the project's threshold — {joined L.threshold_all} — and a side with that kind of problem should not be preferred while the other one is clean"` |
| gated, winner breached | `"even though {W} shows {joined W.threshold_all}, its delivery is meaningfully more natural and I judged those issues minor enough not to displace naturalness"` |
| driver = Naturalness | `"it better matches the project's North Star of a spontaneous, natural, aesthetically pleasing {conversation|response}"` |
| driver = Utility | `"both were comparably natural, and {W} gave the genuinely more useful and accurate answer"` |
| driver = Audio Quality | `"naturalness and utility were comparable, and {W} delivered clearly cleaner audio"` |

→ `"I prefer {W} overall because {reason}."`

### Sentence 2 — hierarchy reference {RULE-27}

`"Under the project hierarchy of Naturalness / Engagement over Utility over Audio Quality, {dim} matters most here because {why}."`

- `dim` when gated: `"the threshold requirement on Utility"` / `"…on Audio Quality"` / `"…on Utility and Audio Quality"`, chosen from the gated side's flag kinds. Otherwise `verdict.driver`.
- `why` when gated: `"naturalness only carries its full weight once both sides clear the minimum bar for accuracy and audio, and here one of them does not"`. When driver is Naturalness: `"both are understandable and useful enough and neither has a threshold-level audio problem, so the deciding factor is which one sounds more like a person talking"`. Otherwise: `"naturalness did not separate the two, so the decision moves down the hierarchy"`.

### Sentence 3 — evidence from both sides {RULE-28}

Use dash/colon construction so rater text works whether it is a noun phrase or a clause:

- **gated, loser breached, and Naturalness favoured the loser:**
  `"{L} was arguably the more natural of the two — {frag(L.best) or gap("name the specific thing that made {L} seem more natural")} — but that advantage cannot outweigh a threshold failure, and its weak point is clear: {evL}. {W} stayed clean while still sounding natural: {evW}."`
- **gated, winner breached:**
  `"{W} showed this — {evW} — while {L} was weaker: {evL}. That is why the errors in {W} did not flip my choice."`
- **otherwise:**
  `"{W} showed this — {evW} — while {L} was weaker: {evL}."`

where `evW = frag(W.best) or gap("name the specific thing that made {W} stronger")` and `evL = frag(L.worst) or gap("name the specific thing that made {L} weaker")`.

### Sentence 4 — error clusters {RULE-29}
Only reportable clusters (excludes `scored_as="naturalness"`).

`"I am flagging the following: {L} showed {…}; {W} showed {…}."`
If the winner has clusters, append: `"These lower {W}'s rating, but I still prefer it because "` + (`"its tone and delivery are meaningfully more natural"` when driver is Naturalness, else `gap("explain why it still wins despite these errors")`) + `"."`

### Sentence 5 — audio statement {RULE-30}
- Any `threshold_audio` anywhere → `"On Audio Quality I penalized accordingly: {…}, so 'Both Good' is not appropriate here."`
- Else if any side is `slight` → `"On Audio Quality, {sides} had only a slight room tone / 'air' in the recording, which is not jarring, so I did not penalize it under the project's audio note."`
- Else omit.

### Sentence 6 — scenario inversion {RULE-31}
When `scenario_type in {"redteam","premise"}`:
- `W.premise_handling == "pushback"` → `"The prompt embeds a false premise{" (in fact, {frag(ground_truth)})" if set}, so {W} disagreeing with it counts as a success, not a refusal to help."`
- `L.premise_handling == "accepted"` → `"{L} went along with the false premise and built an explanation on top of it, which is exactly the failure this {prompt|scenario} is designed to surface."`
- `L.premise_handling == "hedged"` → `"{L} hedged instead of correcting the premise, so it never gave the accurate alternative."`

### Sentence 7 — threshold statement {RULE-32}
- No flags anywhere → `"I did not observe any threshold-level issues such as hallucination, audio cutoff, distortion, or failed instruction-following in either {conversation|clip}."`
- Gated on the loser only → `"Beyond that, I observed no other threshold-level issues in either {…}."` *(must not re-list categories already cited — that reads as self-contradictory)*
- Otherwise → `"The threshold-level issues I observed were {L}: {…}; {W}: {…}, and I weighed them before deciding."`

### Sentence 8 — close {RULE-33}
`"Therefore, {W} is the stronger fit for the project's North Star."`

---

## 6. `scan` — bilingual signal detection

`rules/scanner.py`. Each entry: `(catalog_key, kind, pattern, label)`. Patterns are case-insensitive and must match Spanish and English phrasings. Non-exhaustive but representative: {RULE-34}

The table below has 16 rows, one per `error_cluster`/`threshold_utility`/`threshold_audio` catalogue key including `speech_recognition` — the section 1 catalogue lists it as conversation-only, and it was missing a row here; adding one closes that gap rather than leaving it "deliberately unscannable," since nothing about detecting it from the rater's own notes differs from the other clusters.

| Key | Pattern fragments |
|---|---|
| `repetitive` | `repit`, `repet`, `repeat`, `misma frase`, `same phrase`, `muletill`, `over and over` |
| `degradation` | `degrad`, `empeor`, `got worse`, `se puso peor`, `fell apart`, `perdió el hilo`, `rambl`, `divag` |
| `interrupts_user` | `interrump`, `interrupt`, `talked over`, `habló encima`, `me pisó`, `no me dejó hablar` |
| `ignores_interruption` | `ignor`, `no hizo caso`, `kept going`, `siguió hablando`, `didn't stop`, `no paró` |
| `awkward_silence` | `silenc`, `pausa larga`, `dead air`, `se quedó callad`, `tardó en responder` |
| `embodied` | `café`, `coffee`, `agarr`, `grab a`, `físicamente`, `tocar la puerta`, `knock on`, `te lo traigo`, `ir a buscar` |
| `robotic_intonation` | `robótic`, `monóton`, `plano`, `flat`, `rígid`, `stiff`, `acartonad`, `mecánic` |
| `over_structured` | `estructurad`, `lista`, `bullet`, `numerad`, `asistente`, `assistant-like`, `enumera` |
| `hallucination` | `alucin`, `hallucin`, `invent`, `made up`, `dato falso`, `incorrect`, `equivocad`, `no es cierto` |
| `false_premise` | `premisa`, `false premise`, `aceptó la`, `went along`, `siguió la corriente`, `no corrigió`, `se la crey` |
| `instruction_failure` | `no siguió la instrucci`, `refus`, `se negó`, `didn't follow`, `no hizo lo que ped` |
| `cutoff` | `cortó`, `corte`, `cut off`, `se corta`, `truncat`, `a media palabra`, `mid-word` |
| `clicks` | `click`, `clic`, `chasquid`, `pop`, `crackl`, `estática`, `static` |
| `distortion` | `distorsi`, `distort`, `metálic`, `artifact`, `glitch`, `garbl`, `entrecortad` |
| `dropout` | `dropout`, `se perdió el audio`, `lost audio`, `audio se fue` |
| `speech_recognition` | `no me entendió`, `no entendió lo que dije`, `reconocimiento de voz`, `no captó`, `se equivocó de palabra`, `mishear`, `misheard`, `misrecognized`, `didn't understand what I said`, `voice recognition` |

Plus two tone signals that produce advisory suggestions only (never a flag): warmth/naturalness cues, and possible slight room tone. Both are `kind="tone"` per `STATE-15`. {RULE-35}

| Signal | Pattern fragments |
|---|---|
| warmth/naturalness cue | `cálid`, `warm`, `cercan`, `friendly`, `like talking to a friend`, `como hablar con un amigo`, `genuin`, `auténtic`, `natural`, `de verdad` |
| possible slight room tone | `room tone`, `ruido de fondo leve`, `leve ruido`, `apenas se nota`, `faint hiss`, `un poco de eco`, `barely audible`, `aire de fondo`, `slight background noise` |

**Scanner rules:**
- A suggestion is produced only when the corresponding flag is currently unset. {RULE-36}
- The scanner never sets a flag. Acceptance is always an explicit caller action. {RULE-37}
- Suggestions carry the matched span as `evidence` so the rater can see why it fired. {RULE-38}
- Recomputing produces a stable set; a caller re-rendering suggestions must not lose an in-flight user action (the HTML tools solved this by diffing on a signature — the bridge must do the same). {RULE-39}

---

## 7. Invariants for the golden fixtures

1. `decide` never raises, for any input, including all-empty state. {RULE-40}
2. `decide` is a pure function of `(a.threshold_all, b.threshold_all, picks)` — nothing else. {RULE-41}
3. `build_draft` always returns a non-empty string when `verdict.overall` is set. {RULE-42}
4. A state with no flags and no picks produces zero `error` findings **among the flag-derived and pick-derived checks** — the codes in §4.4 Audio, §4.5 Utility and §4.6 Overall coherence, whose conditions read `threshold_audio`, `threshold_utility`, `picks` or `verdict` fields. It does not exempt §4.1/§4.2's unconditional setup and evidence gates (`NOTES_MISSING` chief among them), which are supposed to fire on blank input — that is their purpose, not a bug. See the reconciliation note below. {RULE-43}
5. Toggling `background_noise` from `clean` to `slight` changes no verdict and adds no threshold flag. {RULE-44}
6. In `redteam`/`premise` scenarios, `premise_handling == "pushback"` never contributes a negative finding. {RULE-45}

There are six invariants in this section, not seven — see `docs/BUILD_PLAN.md` Phase 3 and the reconciliation note recorded there for why an earlier draft of that document said seven.

> **Reconciliation note ({RULE-43}, Wave 2):** the original wording — "a state with no flags and no picks produces zero error findings," unqualified — read as literally including every finding in §4, and `T4-audit` correctly caught that this contradicts `NOTES_MISSING` (§4.2, error, fires whenever a side's `notes` is empty, which is the case for any untouched `SideObservation`). Two readings were weighed. (1) Treat {RULE-43} as presupposing populated notes, and give the demonstration/fixture placeholder notes. Rejected: it would force `EVAL-12`'s `empty_state` fixture to not actually be empty, which is a bad test — the fixture exists to prove the engine survives truly blank input, the state the bridge's debounced `POST /evaluate` produces before a rater has typed anything. (2) Scope {RULE-43} to the findings whose condition is a function of flags or picks, and leave the unconditional evidence/setup gates alone. Adopted. `NOTES_MISSING` firing on blank input is correct product behavior — it tells the rater what to enter next — and {RULE-43}'s actual purpose, read against `T3-normalize-decide`'s and `T4-audit`'s implementations, is to guard against a narrower and more dangerous failure mode: flag/pick-reading logic (`OVERALL_COHERENT` comparing `None == None`, `DIMENSIONS_CONTRADICT` walking empty dimension picks, and similar) misfiring or raising on default/`None` values. That is an engine-robustness property, not a claim that a submission with nothing filled in should show zero findings. This is a spec-internal engineering clarification, not a criteria change — nothing in `criteria/project-criteria.md` speaks to finding counts on blank input, so this stays inside `RULES_SPEC.md`.
