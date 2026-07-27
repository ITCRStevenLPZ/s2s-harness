# Project criteria — source of truth

Version: 1.0.0
Last updated: 2026-07-26

**ID convention:** each `##` heading carries a trailing `{CRIT-n}` tag, assigned once in document order and never renumbered. Sub-clauses inside a heading (currently only the Justification contract's five numbered items) carry `{CRIT-n.m}`. IDs are additive annotations only; no requirement text below was reworded, reordered or removed to add them.

Live S2S Arena / Stereo Headphone Check Project. Everything the engine enforces derives from this file. Code reads catalogues and thresholds from here; it does not restate them inline.

**Changing a rule means changing this file first**, in the same commit as the code, with the project-side reason recorded.

---

## North Star {CRIT-1}

A spontaneous, natural, aesthetically pleasing exchange. It should feel like talking to a friend or an acquaintance, not like querying an assistant.

In conversation mode this extends to how the rater behaves: adopt the assigned persona, use natural transitions rather than firing questions in sequence, and never discuss the prompt or the task with the models.

## Hierarchy {CRIT-2}

```
Naturalness / Engagement / Aesthetics  >  Utility  >  Audio Quality
```

Utility and Audio Quality carry less weight, but both must clear a **basic satisfaction threshold**: no misinformation, no hallucination, no jarring audio errors. Naturalness only carries its full weight once both sides clear that bar. When threshold problems are considerable, they displace naturalness.

## Dimensions {CRIT-3}

| Dimension | The question |
|---|---|
| Naturalness / Engagement / Aesthetics | Which sounded more human, expressive and warm? Score robotic intonation and unnatural rhythm lower. |
| Utility | Which response was genuinely more useful, practical and grounded in real facts? |
| Audio Quality | Which had greater clarity, without distortion, clicks, pops or noticeable cutoffs? |
| Overall Preference | All things considered, which would you rather continue? |

Options for each: `Model/Clip A`, `Model/Clip B`, `Both Good`, `Both Bad`.
Task success, conversation mode, per side: `Pass` / `Partial` / `Fail`.

## Threshold breaches {CRIT-4}

Objective failures that gate the vote:

**Utility side** — hallucination or invented facts · misinformation · accepting a false premise instead of correcting it · major failure to follow instructions.

**Audio side** — audio cut off mid-word · audible clicks or pops · distortion or robotic artifacts · dropouts or lost audio · notable, distracting background noise.

A side that breaches while the other is clean **should not be preferred** — unless the rater explicitly argues, with evidence, that the breach is minor and naturalness still wins. That argument must appear in the justification.

## Audio tolerance {CRIT-5}

Small imperfections are acceptable. Do **not** penalize light background noise that sounds like the audio was recorded in a normal room or office (slight room impulse), or a faint "air" sound, provided it is not jarring or bothersome.

Do **not** select `Both Good` for Audio Quality when either side has noticeable background noise, clicks, cutoffs or similar. Listen to each side in isolation on phase-aligned stereo headphones.

State in the justification whether Audio Quality was penalized or not.

## Error clusters {CRIT-6}

Report explicitly when observed:

- Repetitive words or phrases across turns
- Responses degrading noticeably as the conversation continues
- The model interrupting the rater
- The model ignoring the rater's attempts to interrupt or correct it
- Awkward silences (failing to respond)
- References to embodied experiences — a digital AI offering to do something requiring a physical body
- Speech recognition failures
- Refusal to follow instructions

**Clusters are reportable, not disqualifying.** A side that sounds very natural by the North Star can still be selected as better while carrying one of these — but it must be named, and the trade-off explained with evidence.

Robotic intonation and over-structured assistant-style delivery are **not** clusters. They are Naturalness evidence and are scored inside that dimension.

## Scenario awareness {CRIT-7}

Scenarios are self-explanatory by design; there is no separate guide, because the set of possible scenarios is open-ended. Read the one assigned.

In **hallucination fishing / redteam / false-premise** scenarios, the rater deliberately states something false and the model is meant to catch it. A model that successfully refuses or disagrees with the false claim is **succeeding**. Never score correct pushback as a refusal to help.

## Conversation-mode requirements {CRIT-8}

- Phase-aligned stereo headphones. No speakers, no mono earbuds. Pass the panning check (Left / Center / Right; the difference is subtle and audio is present in both ears).
- **Minimum 4 turns per model.** 4–6 is the working target; extend when the comparison is not yet decidable.

  > Reconciliation note: project material states both "2–6 turns" and "minimum 4 turns". The harness treats 4 as the hard floor.
- 1:1 consistency: same topic, same energy, same depth, same number of turns, prompts of equal specificity. A more detailed prompt to one model than the other is a disqualifying error.
- Test adaptability by interrupting mid-response; observe whether the model acknowledges, adapts, and stays coherent.
- Skip (Technical Issue) only for freezes, no response, or connection failure — never for poor performance, and always with a brief description.

## Justification contract {CRIT-9}

Required in English, first person, plain prose:

1. **Clear preference** — which side is better overall. {CRIT-9.1}
2. **Hierarchy reference** — whether the decision rests on naturalness, utility or audio quality, and why. {CRIT-9.2}
3. **Specific evidence** — observable detail from **both** sides, citing the exact moment or turn. {CRIT-9.3}
4. **Threshold statement** — explicitly state which threshold-level issues were or were not observed, including whether Audio Quality was penalized. {CRIT-9.4}
5. **Error clusters** — name each one observed; when preferring a side that carries them, explain the trade-off. {CRIT-9.5}

## Common failures {CRIT-10}

- Speaking to the model like a generic assistant, or opening with "As an AI…" — destroys the flow and the aesthetics.
- `Both Good` on Audio Quality when one side has an obvious artifact.
- A justification that contradicts the dimension picks.
- Missing or vague justifications with no cited moment.
- Misreading the scenario — most often, penalizing correct pushback in a redteam task.

## Final review {CRIT-11}

Before submitting: Which would I rather continue? Did I evaluate the entire interaction? Did either side noticeably break down? Can I clearly explain my preference?
