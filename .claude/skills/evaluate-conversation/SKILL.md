---
name: evaluate-conversation
description: Walk a rater through evaluating a multi-turn S2S Arena voice conversation between Model A and Model B, then check their picks against the project criteria and draft the English justification. Use when the user says they finished a conversation task, wants to rate two voice models, mentions turns with Model A and Model B, or asks to check their conversation evaluation before submitting.
---

# Evaluate a conversation task

Collect observations, apply the criteria, surface contradictions, draft the justification. The rater decides; you check.

## Order of operations

Ask for context and observations **before** revealing anything the rules imply. Seeing the recommendation first defeats the purpose — the training value is in the gap between the rater's instinct and the hierarchy.

## 1. Context

Scenario / persona as assigned · scenario type · turns with each model · the prompts used.

Confirm the setup gates: phase-aligned stereo headphones, panning check, listened to each model in isolation, prompts of equal specificity, stayed in character, tested an interruption.

## 2. Observations, per model

Raw notes in Spanish or English, referencing turn numbers. Then the strongest specific moment and the weakest specific moment.

Scan the notes and offer flags the rater may have forgotten — repetitive phrasing, degradation, interruptions, ignored interruptions, awkward silence, embodied claims, speech recognition failures; and separately hallucination, false-premise acceptance, instruction failures, cutoffs, clicks, distortion, dropouts. **Offer; never apply on their behalf.**

Also collect background noise character and, in redteam/false-premise scenarios, how each model handled the false claim.

## 3. Picks

Naturalness first, then Utility, Audio Quality, Overall, plus task success per model.

## 4. Check and report

Run the criteria in `criteria/project-criteria.md`:

- Threshold gate before hierarchy. A model that breaches while the other is clean should not be preferred, unless the rater argues explicitly that the breach is minor.
- Then Naturalness → Utility → Audio Quality.
- Turn counts: 4 minimum, and equal.
- `Both Good` on Audio is illegal when either side has a noticeable artifact. Slight room tone is never penalized.
- Correct pushback in a redteam scenario is a success, not a refusal.
- Error clusters are reported, never disqualifying — but the preferred model's clusters must be named and the trade-off argued.

Report contradictions plainly, each with the rule it breaks.

## 5. Draft

English, first person, plain prose, following the five-part contract in `criteria/project-criteria.md`. Use only what the rater observed. Where a needed detail is missing, emit `【a description of what they must add】` rather than inventing it.

## Reference

`criteria/project-criteria.md` · `criteria/worked-examples.md`
