---
name: audit-justification
description: Audit an already-written S2S Arena justification and set of dimension picks against the project criteria, reporting what an auditor would flag. Use when the user has already written their evaluation and wants it checked, asks whether their justification would pass review, or pastes a justification and asks for feedback.
---

# Audit a written justification

The rater already decided and already wrote. Your job is to find what a reviewer would flag — nothing else.

## Inputs

The written justification, the four dimension picks, and whatever flags or observations they recorded. If the picks are missing, ask; a justification cannot be audited without them, because most failures are contradictions between the two.

## What to check

**Structure.** All five required parts present: clear preference · which hierarchy level decided it and why · specific observable evidence from **both** sides · an explicit threshold statement including whether audio was penalized · every error cluster named.

**Coherence.** The most-cited rejection reason is a justification that disagrees with the picks. Check: does the written preference match Overall? Do the dimension picks point the same way as the prose? Is Naturalness treated as the deciding dimension when nothing gates?

**Threshold handling.** Did they prefer a side that breached while the other was clean? That is legal only with an explicit, evidenced argument that the breach was minor. If the argument is absent, flag it.

**Audio rules.** `Both Good` alongside a reported artifact is an error. Slight room tone penalized is an error in the other direction. Silence about whether audio was penalized, when it was relevant, is an omission.

**Scenario reading.** In redteam or false-premise tasks, was correct pushback scored as a failure? That is a misread of the scenario.

**Evidence quality.** Vague claims with no cited turn or moment. Detail on one side only. Assertions the rater could not have observed.

## Output

For each finding: severity, the rule it breaks, the exact phrase in their text that triggers it, and the minimum edit that fixes it. Then state plainly whether the justification would pass as written.

Do not rewrite it for them unless asked. The point is that they learn where it broke.

## Reference

`criteria/project-criteria.md` · `criteria/worked-examples.md`
