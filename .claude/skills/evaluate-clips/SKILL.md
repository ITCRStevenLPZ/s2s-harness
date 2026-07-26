---
name: evaluate-clips
description: Compare two single audio responses (Clip A and Clip B) to the same prompt using the S2S Arena criteria, check the rater's picks for contradictions, and draft the English justification. Use when the user has two clips rather than a conversation, mentions Clip A and Clip B, or is doing a single-response audio comparison task.
---

# Evaluate a clip comparison

Same criteria as a conversation task, minus everything conversational. No turns, no 1:1 consistency, no interruption test — just two responses to one prompt.

## 1. The prompt

What was asked, the prompt type, and — when the prompt embeds a false claim — the ground truth. That last field is what separates a correct pushback from an unhelpful refusal, so ask for it.

## 2. Observations, per clip

Notes in Spanish or English, then the strongest and weakest thing about the clip.

Offer flags from the notes: repetitive phrasing, a response that fell apart, awkward silence, embodied claims, robotic intonation, over-structured assistant-style delivery; and separately hallucination, false-premise acceptance, instruction failure, cutoff, clicks, distortion, dropouts. Offer, never apply.

Plus background noise character and how the clip handled any false claim.

> Robotic intonation and over-structured delivery are **Naturalness evidence**, not reportable error clusters. Cite them as evidence in the justification; do not report them as errors.

## 3. Picks

Naturalness, Utility, Audio Quality, Overall.

## 4. Check and report

- Threshold gate first, then the hierarchy.
- `Both Good` on Audio is illegal when either clip has a noticeable artifact; slight room tone is never penalized.
- A clip that corrects a false premise is succeeding.
- Utility cannot be awarded to a clip flagged for hallucination or false-premise acceptance.
- Overall must not contradict two of three dimensions.

## 5. Draft

Five-part contract, English, first person. `【placeholders】` for anything the rater did not supply.

## Reference

`criteria/project-criteria.md` · `criteria/worked-examples.md`
