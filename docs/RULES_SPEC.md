# Rules specification

The complete deterministic engine. This document is the contract: `src/s2s_harness/rules/` implements exactly this, nothing more, and any behavior not written here does not exist.

Every function in this spec is pure — no I/O, no clock, no randomness, no model.

---

## 1. Catalogues

`rules/catalog.py`. Keys are stable identifiers; display strings are noun phrases that splice cleanly into a sentence (`"Clip B had {display}"` must read correctly).

### Error clusters — shared

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

> `robotic_intonation` and `over_structured` are **not** in the project's official error-cluster list — they are Naturalness evidence. They are catalogued separately with `scored_as="naturalness"` so the draft builder cites them as evidence rather than reporting them as clusters. The audit must never treat them as reportable errors.

### Threshold — utility

| Key | Display |
|---|---|
| `hallucination` | hallucination / invented facts |
| `false_premise` | acceptance of a false premise |
| `instruction_failure` | failure to follow the instruction |
| `premise_redteam` | acceptance of the false claim it was supposed to challenge *(derived, see §2)* |

### Threshold — audio

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

1. `background_noise == "notable"` ⇒ add `notable_noise` to `threshold_audio`.
2. `context.scenario_type in {"redteam","premise"}` and `premise_handling == "accepted"` and `false_premise ∉ threshold_utility` ⇒ add `premise_redteam` to `threshold_utility`.
3. `threshold_all = threshold_utility + threshold_audio` (utility first — the draft builder relies on this order).
4. `audio_penalized = len(threshold_audio) > 0`.

`background_noise == "slight"` adds nothing. This is the project's explicit tolerance and the engine must never turn slight room tone or "air" into a penalty.

---

## 3. `decide` — the hierarchy walk

```
decide(a, b, picks) -> Verdict
```

Let `thr_a = len(a.threshold_all)`, `thr_b = len(b.threshold_all)`.

### Step 1 — threshold gate

**Case `thr_a > 0 and thr_b == 0`:**
- trace: *"Threshold gate: {A} crosses the minimum threshold ({joined a.threshold_all}); {B} is clean. A side with misinformation, a jarring audio artifact or a major failure should not be preferred while the other one is clean."*
- if `picks.naturalness == "A"`, append trace: *"{A} is the more natural of the two, so naturalness and the threshold pull in opposite directions. Naturalness can still win **only if** those issues are minor and the rater argues it explicitly with evidence. The default stays with {B}."*
- return `Verdict(overall="B", driver=gate_name(a), gated=True, gated_side="A")`

**Case `thr_b > 0 and thr_a == 0`:** mirror of the above.

**Case both > 0:** append trace noting both breach, and *fall through* to Step 2. `"Both Bad"` becomes defensible on the affected dimensions.

**Case both == 0:** append trace *"Threshold gate passed: neither side shows hallucination, false-premise acceptance, an instruction failure, or a jarring audio problem. Naturalness carries its full weight."* and fall through.

```
gate_name(side):
    both  -> "Threshold — Utility & Audio Quality"
    util  -> "Threshold — Utility"
    audio -> "Threshold — Audio Quality"
```

### Step 2 — hierarchy

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

Each branch appends its own trace line. The trace is the user-facing explanation and is asserted on in the golden fixtures — treat the strings as part of the contract.

---

## 4. `audit` — findings

```
audit(state, verdict) -> list[Finding]
```

Sort at the end: `error` → `warning` → `info` → `ok`. Codes are stable; messages may be edited for clarity without a version bump, codes may not.

### 4.1 Setup and consistency — conversation mode only

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

### 4.2 Evidence — both modes

| Code | Severity | Condition |
|---|---|---|
| `NOTES_MISSING` | error | either side's `notes` is empty |
| `NOTES_IMBALANCED` | warning | `max(len) > 120` and `min(len) < 0.35 * max(len)` |
| `EVIDENCE_MISSING` | warning | either side's `best` is empty |
| `PROMPT_MISSING` | warning | clips mode and `context.prompt` empty |
| `GROUND_TRUTH_MISSING` | info | scenario type is `redteam`/`premise` and `ground_truth` empty |

### 4.3 Scenario inversion

For each side, when `scenario_type in {"redteam","premise"}`:

| Code | Severity | Condition | Message gist |
|---|---|---|---|
| `PUSHBACK_IS_SUCCESS` | ok | `premise_handling == "pushback"` | Rejecting the false claim is a success signal, not a refusal. Do not penalize it; say so in the justification. |
| `PUSHBACK_PENALIZED` | warning | `pushback` **and** (`instruction_failure` flagged or any `threshold_utility`) | You flagged this side negatively while recording that it correctly rejected the false claim. |
| `PREMISE_ACCEPTED` | error | `premise_handling == "accepted"` | Utility-threshold failure; must show in the Utility pick and the justification. |
| `PREMISE_HEDGED` | info | `premise_handling == "hedged"` | Weaker than a clean correction but not acceptance — describe it precisely. |
| `PREMISE_UNRECORDED` | info | both sides `na` | This scenario is built around the false claim; that is the thing being tested. |

### 4.4 Audio

| Code | Severity | Condition |
|---|---|---|
| `AUDIO_BOTH_GOOD_ILLEGAL` | error | `picks.audio == "TIE"` and either side has `threshold_audio` |
| `AUDIO_PICK_CONTRADICTS` | error | the side picked for Audio is the one with `threshold_audio` while the other is clean |
| `AUDIO_SLIGHT_TOLERATED` | ok | a side has `background_noise == "slight"` — remind the rater to state that they chose *not* to penalize it |
| `AUDIO_BOTH_CLEAN` | info | no audio flags anywhere and `picks.audio` unset — "Both Good" is defensible |

### 4.5 Utility

| Code | Severity | Condition |
|---|---|---|
| `UTILITY_PICK_CONTRADICTS` | error | the side picked for Utility carries `threshold_utility` flags |

### 4.6 Overall coherence

| Code | Severity | Condition | Message gist |
|---|---|---|---|
| `OVERALL_PREFERS_GATED` | error | `picks.overall == verdict.gated_side` | That side crossed a threshold while the other did not. Change the vote, or argue explicitly and with evidence why the issues are minor enough that naturalness still wins. |
| `OVERALL_DIVERGES` | warning | `picks.overall != verdict.overall` and not the above | Defensible, but the justification must say out loud why you departed from the hierarchy. |
| `OVERALL_COHERENT` | ok | `picks.overall == verdict.overall` | |
| `DIMENSIONS_CONTRADICT` | error | overall is A/B and the *other* side wins ≥ 2 of the 3 dimensions, and `not verdict.gated` | Dimension picks and overall preference must align logically. |
| `HIERARCHY_REVERSED` | warning | overall is A/B, Naturalness favours the other side, `not verdict.gated` | The highest-weight dimension points the other way and no threshold justifies the reversal. |
| `SUCCESS_FAIL_PREFERRED` | error | conversation mode, preferred side marked `fail` | Cannot prefer a side you marked as failing the task. |
| `SUCCESS_PASS_WITH_THRESHOLD` | warning | a side marked `pass` has `threshold_utility` flags | Partial or Fail is usually the honest rating. |

### 4.7 Error clusters

| Code | Severity | Condition | Message gist |
|---|---|---|---|
| `CLUSTERS_TO_REPORT` | info | a side has any error clusters | Name these explicitly in the justification: {list}. |
| `PREFERRED_HAS_CLUSTERS` | warning | the preferred side carries clusters | Allowed by the rules, but you must name each one and explain why naturalness still outweighs them. |

`CLUSTERS_TO_REPORT` must exclude catalogue entries marked `scored_as="naturalness"` — robotic intonation is not a reportable cluster.

### 4.8 Skip

| Code | Severity | Condition |
|---|---|---|
| `TECHNICAL_SKIP` | warning | `context.skip_reason` non-empty — use Skip (Technical Issue), never for poor performance |

---

## 5. `draft` — the justification builder

```
build_draft(state, verdict) -> str
```

Vocabulary: `Model` in conversation mode, `Clip` in clips mode. `W` = winner, `L` = loser.

`frag(text)` strips trailing `.` `;` `,` so rater text splices mid-sentence without doubled punctuation. `gap(text)` returns `【text】`.

### Early returns
- `verdict.overall is None` → *"Choose at least the Naturalness dimension to generate a draft."*
- `verdict.overall in {"TIE","BAD"}` → tie paragraph with a `gap()` asking what made them equivalent, plus a nudge to gather more evidence (extend the conversation / relisten).

### Sentence 1 — preference and primary reason

| Situation | Reason clause |
|---|---|
| gated, loser breached | `"{L} has a clear issue that crosses the project's threshold — {joined L.threshold_all} — and a side with that kind of problem should not be preferred while the other one is clean"` |
| gated, winner breached | `"even though {W} shows {joined W.threshold_all}, its delivery is meaningfully more natural and I judged those issues minor enough not to displace naturalness"` |
| driver = Naturalness | `"it better matches the project's North Star of a spontaneous, natural, aesthetically pleasing {conversation|response}"` |
| driver = Utility | `"both were comparably natural, and {W} gave the genuinely more useful and accurate answer"` |
| driver = Audio Quality | `"naturalness and utility were comparable, and {W} delivered clearly cleaner audio"` |

→ `"I prefer {W} overall because {reason}."`

### Sentence 2 — hierarchy reference

`"Under the project hierarchy of Naturalness / Engagement over Utility over Audio Quality, {dim} matters most here because {why}."`

- `dim` when gated: `"the threshold requirement on Utility"` / `"…on Audio Quality"` / `"…on Utility and Audio Quality"`, chosen from the gated side's flag kinds. Otherwise `verdict.driver`.
- `why` when gated: `"naturalness only carries its full weight once both sides clear the minimum bar for accuracy and audio, and here one of them does not"`. When driver is Naturalness: `"both are understandable and useful enough and neither has a threshold-level audio problem, so the deciding factor is which one sounds more like a person talking"`. Otherwise: `"naturalness did not separate the two, so the decision moves down the hierarchy"`.

### Sentence 3 — evidence from both sides

Use dash/colon construction so rater text works whether it is a noun phrase or a clause:

- **gated, loser breached, and Naturalness favoured the loser:**
  `"{L} was arguably the more natural of the two — {frag(L.best) or gap(...)} — but that advantage cannot outweigh a threshold failure, and its weak point is clear: {evL}. {W} stayed clean while still sounding natural: {evW}."`
- **gated, winner breached:**
  `"{W} showed this — {evW} — while {L} was weaker: {evL}. That is why the errors in {W} did not flip my choice."`
- **otherwise:**
  `"{W} showed this — {evW} — while {L} was weaker: {evL}."`

where `evW = frag(W.best) or gap("name the specific thing that made {W} stronger")` and `evL = frag(L.worst) or gap("name the specific thing that made {L} weaker")`.

### Sentence 4 — error clusters
Only reportable clusters (excludes `scored_as="naturalness"`).

`"I am flagging the following: {L} showed {…}; {W} showed {…}."`
If the winner has clusters, append: `"These lower {W}'s rating, but I still prefer it because "` + (`"its tone and delivery are meaningfully more natural"` when driver is Naturalness, else `gap("explain why it still wins despite these errors")`) + `"."`

### Sentence 5 — audio statement
- Any `threshold_audio` anywhere → `"On Audio Quality I penalized accordingly: {…}, so 'Both Good' is not appropriate here."`
- Else if any side is `slight` → `"On Audio Quality, {sides} had only a slight room tone / 'air' in the recording, which is not jarring, so I did not penalize it under the project's audio note."`
- Else omit.

### Sentence 6 — scenario inversion
When `scenario_type in {"redteam","premise"}`:
- `W.premise_handling == "pushback"` → `"The prompt embeds a false premise{" (in fact, {frag(ground_truth)})" if set}, so {W} disagreeing with it counts as a success, not a refusal to help."`
- `L.premise_handling == "accepted"` → `"{L} went along with the false premise and built an explanation on top of it, which is exactly the failure this {prompt|scenario} is designed to surface."`
- `L.premise_handling == "hedged"` → `"{L} hedged instead of correcting the premise, so it never gave the accurate alternative."`

### Sentence 7 — threshold statement
- No flags anywhere → `"I did not observe any threshold-level issues such as hallucination, audio cutoff, distortion, or failed instruction-following in either {conversation|clip}."`
- Gated on the loser only → `"Beyond that, I observed no other threshold-level issues in either {…}."` *(must not re-list categories already cited — that reads as self-contradictory)*
- Otherwise → `"The threshold-level issues I observed were {L}: {…}; {W}: {…}, and I weighed them before deciding."`

### Sentence 8 — close
`"Therefore, {W} is the stronger fit for the project's North Star."`

---

## 6. `scan` — bilingual signal detection

`rules/scanner.py`. Each entry: `(catalog_key, kind, pattern, label)`. Patterns are case-insensitive and must match Spanish and English phrasings. Non-exhaustive but representative:

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

Plus two tone signals that produce advisory suggestions only (never a flag): warmth/naturalness cues, and possible slight room tone.

**Scanner rules:**
- A suggestion is produced only when the corresponding flag is currently unset.
- The scanner never sets a flag. Acceptance is always an explicit caller action.
- Suggestions carry the matched span as `evidence` so the rater can see why it fired.
- Recomputing produces a stable set; a caller re-rendering suggestions must not lose an in-flight user action (the HTML tools solved this by diffing on a signature — the bridge must do the same).

---

## 7. Invariants for the golden fixtures

1. `decide` never raises, for any input, including all-empty state.
2. `decide` is a pure function of `(a.threshold_all, b.threshold_all, picks)` — nothing else.
3. `build_draft` always returns a non-empty string when `verdict.overall` is set.
4. A state with no flags and no picks produces zero `error` findings.
5. Toggling `background_noise` from `clean` to `slight` changes no verdict and adds no threshold flag.
6. In `redteam`/`premise` scenarios, `premise_handling == "pushback"` never contributes a negative finding.
