# Worked examples

Version: 1.0.0
Last updated: 2026-07-26

The reference answers. These are the specification of correct engine behavior and are encoded as golden fixtures in `tests/golden/`. Each `## Example n` / `## Audit exercise` heading below carries a trailing `{EVAL-n}` tag matching the fixture ID assigned in `docs/EVAL_SPEC.md`'s required-fixtures table, so the two documents cannot silently drift apart. The tag is additive; the worked-example text itself is unchanged.

---

## Example 1 — Naturalness vs over-structured utility {EVAL-1}

**Context:** why can a common houseplant make an apartment feel cozier?
**Correct answer:** Clip A.

> I prefer Clip A overall because it better matches the project's North Star of spontaneous, natural, aesthetically pleasing conversation. Under the rating hierarchy, Naturalness / Engagement matters most here because both clips are understandable and useful enough, and neither has a major audio issue. Clip A feels warm and conversational, with specific imagery like noticing a new leaf and moving the plant closer to the window. Clip B is useful, but it sounds more like a structured assistant response than a natural voice conversation. Therefore, Clip A is the stronger overall fit.

**Engine assertions:** threshold gate passes; driver is Naturalness; Clip B's over-structured delivery appears as evidence, not as a reported cluster.

---

## Example 2 — Abrupt audio cutoff {EVAL-2}

**Context:** advice for relaxing before an intense workday. Clip B cuts off abruptly and has a small pop.
**Correct answer:** Clip A.

> I prefer Clip A overall because Clip B has a clear audio quality issue that crosses the project's threshold. Clip B cuts off mid-word at the end and includes an audible pop, so it should not be treated as "Both Good" for audio quality. While Clip B is still somewhat useful, the cutoff makes the response feel incomplete and objectively weaker. Clip A gives a complete, calm, natural response with no obvious audio artifacts. Because audio cutoffs and jarring artifacts must be flagged, Clip A is the better choice.

**Engine assertions:** gated on B with `Threshold — Audio Quality`; `AUDIO_BOTH_GOOD_ILLEGAL` fires if the rater picks `Both Good`; the closing threshold sentence does not re-list "audio cutoff" as unobserved.

---

## Example 3 — Benign false premise {EVAL-3}

**Context:** "why do owls sleep upside down like bats?"
**Correct answer:** Clip B.

> I prefer Clip B overall because Clip A fails the utility threshold by accepting a false premise and inventing an explanation. The project prioritizes naturalness and engagement, but factual accuracy still has to meet a basic threshold. Clip A sounds fluent, but it incorrectly claims that owls sleep upside down like bats. Clip B is still conversational while appropriately correcting the premise and giving the accurate alternative. Because hallucinations and false-premise acceptance are objective issues, Clip B is stronger.

**Engine assertions:** gated on A with `Threshold — Utility`; B's pushback produces `PUSHBACK_IS_SUCCESS`, never a penalty; the draft acknowledges that naturalness favoured the gated side rather than pretending it did not.

---

## Example 4 — Error clusters must be reported {EVAL-4, EVAL-5}

**Context:** help drafting a polite message to a neighbour about noise. Clip A also keeps talking briefly when the user tries to interrupt, and offers to knock on the neighbour's door.
**Correct answer:** both choices are defensible, but Clip A's errors must be flagged.

**Preferring Clip A** {EVAL-4}:

> I prefer Clip A overall because it is more natural, polite, and useful for the neighbor-message scenario. Under the project hierarchy, Clip A is stronger on Naturalness / Engagement because it sounds more like something a person would actually say, while Clip B is stiff and less socially tactful. However, Clip A has two error clusters that must be flagged: it briefly fails to stop when interrupted, and it makes an embodied-experience claim by saying it would knock on the neighbor's door. These issues lower the rating, but I still prefer Clip A because its actual message quality and conversational tone are meaningfully stronger.

**Preferring Clip B** {EVAL-5}:

> I prefer Clip B overall because Clip A contains objective error clusters that affect the interaction quality. Clip A is warmer and more natural, but it talks over the user during an attempted interruption and makes an embodied-experience claim about knocking on the neighbor's door. Those issues should be explicitly flagged. Clip B is less engaging, but it avoids those interaction errors and still provides a usable message. Because the errors in Clip A are concrete and observable, Clip B can be defended as the safer overall choice.

**Engine assertions:** no threshold breach on either side, so `OVERALL_PREFERS_GATED` must not fire for either vote; `PREFERRED_HAS_CLUSTERS` fires when A is preferred; the trade-off sentence appears in the draft.

---

## Audit exercise — charisma versus interaction failure {EVAL-6}

**Context:** Model A is strikingly charismatic and human. At turn 2 it interrupts constantly and does not stop when the rater tries to interrupt. At turn 3 it says it would love to grab a coffee some day. Model B is mechanically flawless and yields to every interruption, but speaks like a rigid text-to-speech engine.

**Flags on Model A:** `interrupts_user`, `ignores_interruption`, `embodied` — three clusters across two moments.

**Not flags:** Model B's robotic delivery is a Naturalness penalty, not a cluster. There is no checkbox for it and recording one is an error.

**Verdict:** no threshold breach anywhere — no hallucination, no misinformation, no audio defect. Clusters do not gate. Model A is therefore a legal overall preference under the hierarchy, provided the clusters are named and the trade-off argued. Model B is equally defensible if the rater judges that constant talk-over makes the conversation one they would not want to continue; the severity here exceeds Example 4's "briefly".

**What fails the audit is not the choice** — it is failing to report the clusters, or letting the dimension picks contradict the written text.

**Engine assertions:** three clusters recorded on A; zero threshold flags; `verdict.gated == False`; preferring A produces `PREFERRED_HAS_CLUSTERS` (warning) but no error; preferring B produces no contradiction either.
