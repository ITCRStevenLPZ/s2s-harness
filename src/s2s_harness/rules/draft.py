"""The justification builder: `build_draft(state, verdict) -> str`.

Implements `docs/RULES_SPEC.md` section 5, {RULE-24} through {RULE-33},
against the Wave-2 (version 1.1.0) text that closed gaps 1 and 5 (the
TIE/BAD paragraph and the sentence-3 variant-1 gap text -- see
`team_findings.md`, "[T1] Gaps 1, 5, 6 CLOSED").

Zero LLM calls, zero I/O, zero network, zero clock, zero randomness.
Imports: stdlib, Pydantic (via `models.state`) and `rules.catalog` only,
per CLAUDE.md design rules 1 and 2, and `docs/ARCHITECTURE.md`'s layer
table (`rules/` may import `models/`, never the reverse).

This module never reads `verdict.trace` and never talks to `rules/decide.py`
or `rules/audit.py` directly -- it takes `EvaluationState` and `Verdict` as
plain data, per the "state is the only contract between nodes" rule in
CLAUDE.md's graph conventions.

Determinism: every list this module builds for output (threshold-key
joins, cluster joins, side clauses) iterates a fixed-order list or tuple
(`SideObservation.threshold_all` / `.error_clusters` preserve caller
order; `catalog.REPORTABLE_ERROR_CLUSTERS` is a tuple in catalogue-table
order) -- never a `set` or an unordered `dict`, per CLAUDE.md's
determinism rule and {RULE-41}'s sibling invariant for `draft`.
"""

from __future__ import annotations

from typing import cast

from s2s_harness.models.state import EvaluationState, Mode, Side, SideObservation, Verdict
from s2s_harness.rules import catalog

# ---------------------------------------------------------------------------
# RULE-24: frag() / gap()
# ---------------------------------------------------------------------------

# The exact CJK bracket pair from CLAUDE.md design rule 4 / RULES_SPEC
# {RULE-24}. Guarded token form -- never change these two characters.
_GAP_OPEN = "【"
_GAP_CLOSE = "】"

# {RULE-24}: "frag(text) strips trailing . ; , so rater text splices
# mid-sentence without doubled punctuation." Stripped iteratively (not a
# single `rstrip` call limited to one pass) so a rater note ending in
# ".," or ".." -- the exact doubled-punctuation bug this rule exists to
# prevent -- is fully cleaned, not left with one trailing mark.
_TRAILING_STRIP_CHARS = ".,;"


def frag(text: str) -> str:
    """RULES_SPEC section 5, {RULE-24}: strip trailing `.` `;` `,` (and any
    whitespace uncovered by doing so) for mid-sentence splicing.

    Returns "" for whitespace-only or fully-punctuation input, so the
    idiom `frag(x) or gap(...)` (used throughout this module, per
    {RULE-28}) falls back to a placeholder instead of splicing an empty
    fragment.
    """
    result = text.strip()
    while result and result[-1] in _TRAILING_STRIP_CHARS:
        result = result[:-1].rstrip()
    return result


def gap(text: str) -> str:
    """RULES_SPEC section 5, {RULE-24}: the exact placeholder token form
    from CLAUDE.md design rule 4. Never invent an observation -- this is
    the only sanctioned way to mark one missing.
    """
    return f"{_GAP_OPEN}{text}{_GAP_CLOSE}"


# ---------------------------------------------------------------------------
# Vocabulary: "Model" in conversation mode, "Clip" in clips mode.
# RULES_SPEC section 5, opening paragraph.
# ---------------------------------------------------------------------------

_NOUN_CONVERSATION = "Model"
_NOUN_CLIPS = "Clip"


def _noun(mode: Mode) -> str:
    return _NOUN_CONVERSATION if mode == "conversation" else _NOUN_CLIPS


def _label(mode: Mode, side: Side) -> str:
    """`"{Model|Clip} {A|B}"` -- the `W` / `L` / `A` / `B` display used
    throughout every sentence slot below.
    """
    return f"{_noun(mode)} {side}"


def _interaction_noun(mode: Mode) -> str:
    """Sentence 1's `{conversation|response}` placeholder ({RULE-26}):
    what kind of exchange the North Star describes. Conversation mode is
    literally a conversation; a single clip is a response to a prompt,
    not a conversation, so clips mode says "response".
    """
    return "conversation" if mode == "conversation" else "response"


def _artifact_noun(mode: Mode) -> str:
    """Sentence 7's `{conversation|clip}` placeholder ({RULE-32}): the
    artifact under review, distinct from `_interaction_noun` (sentence 1
    describes exchange *quality*; sentence 7 names the *thing being
    listened to*).
    """
    return "conversation" if mode == "conversation" else "clip"


def _task_noun(mode: Mode) -> str:
    """Sentence 6's `{prompt|scenario}` placeholder ({RULE-31}), matching
    `TaskContext`'s own field names: clips mode carries `context.prompt`
    (the question the clips answer); conversation mode carries
    `context.scenario` (the assigned scenario/persona).
    """
    return "prompt" if mode == "clips" else "scenario"


# ---------------------------------------------------------------------------
# Verdict.driver literal strings. RULES_SPEC section 3, {RULE-14}/{RULE-15}
# (transcribed here, not imported from rules/decide.py -- draft.py takes
# `Verdict` as data per the graph's "state is the only contract" rule and
# does not depend on decide.py's internals).
# ---------------------------------------------------------------------------

_DRIVER_NATURALNESS = "Naturalness / Engagement"
_DRIVER_UTILITY = "Utility"
_DRIVER_AUDIO = "Audio Quality"

# RULES_SPEC section 1: the two closed catalogues that partition every key
# that can appear in threshold_all. Used only for kind-of-breach
# membership tests (sentence 2's gated `dim`), never iterated for output
# order.
_UTILITY_KEYS: frozenset[str] = frozenset(catalog.THRESHOLD_UTILITY_KEYS)
_AUDIO_KEYS: frozenset[str] = frozenset(catalog.THRESHOLD_AUDIO_KEYS)


# ---------------------------------------------------------------------------
# Shared list-join helper. RULES_SPEC section 3, {RULE-47} (`joined()`):
# single item as itself; two items "X and Y"; three or more as an
# Oxford-comma list. RULE-47 defines this for `decide`'s traces; sentence 1
# ({RULE-26}) reuses `{joined L.threshold_all}` / `{joined W.threshold_all}`
# in the draft itself, so the same convention is reproduced here rather
# than imported from `rules/decide.py` (each rules/ module stays
# self-contained; only `EvaluationState`/`Verdict` cross the boundary).
# ---------------------------------------------------------------------------


def _join_english(items: list[str]) -> str:
    """{RULE-47}'s join convention, reproduced for this module's own use."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _threshold_display(key: str) -> str:
    """Look up a threshold catalogue key's display string in either
    catalogue (RULES_SPEC section 1). Falls back to the raw key so this
    function -- and therefore `build_draft` -- cannot raise on an
    unvalidated key, mirroring `rules/decide.py`'s `_display_for` and
    preserving {RULE-42} (always non-empty) even on malformed input.

    `key` is a plain `str` (from `SideObservation.threshold_all: list[str]`,
    not the narrower `Literal` catalogue key types), so `.get()` cannot
    resolve to a single overload -- the `call-overload` ignore below is
    the real error `mypy` reports for that mismatch, not `arg-type`.
    """
    utility_entry = catalog.THRESHOLD_UTILITY.get(key)  # type: ignore[call-overload]
    if utility_entry is not None:
        return str(utility_entry.display)
    audio_entry = catalog.THRESHOLD_AUDIO.get(key)  # type: ignore[call-overload]
    if audio_entry is not None:
        return str(audio_entry.display)
    return key


def _joined_threshold(keys: list[str]) -> str:
    """`{joined ...}` over a `threshold_all`/`threshold_audio`-style list.

    Preserves the caller's existing order (utility keys first, per
    {RULE-7}) instead of sorting -- required for determinism and for
    sentence 1's "name the breach category first" reliance on that order.
    """
    return _join_english([_threshold_display(key) for key in keys])


def _reportable_clusters_for(side: SideObservation) -> list[str]:
    """The side's error-cluster keys that are reportable, in catalogue
    order. RULES_SPEC section 1 note + {RULE-2}/{RULE-22.1}: entries
    marked `scored_as="naturalness"` (`robotic_intonation`,
    `over_structured`) are Naturalness evidence, never a reportable
    cluster, so `catalog.REPORTABLE_ERROR_CLUSTERS` already excludes them.

    Iterates the fixed catalogue tuple (not the side's own list, and not a
    set) so cluster order in the rendered sentence is always the
    catalogue's table order, deterministic across runs.
    """
    present = set(side.error_clusters)
    return [key for key in catalog.REPORTABLE_ERROR_CLUSTERS if key in present]


def _clusters_display(keys: list[str], mode: Mode) -> str:
    """Display strings for a list of (already-filtered reportable)
    error-cluster keys, mode-aware. Same `call-overload` reasoning as
    `_threshold_display`: `keys` holds plain `str`, not the catalogue's
    `Literal` key type.
    """
    displays: list[str] = []
    for key in keys:
        entry = catalog.ERROR_CLUSTERS.get(key)  # type: ignore[call-overload]
        if entry is not None:
            displays.append(str(entry.display(mode)))
        else:
            displays.append(key)
    return _join_english(displays)


# ---------------------------------------------------------------------------
# Early returns. RULES_SPEC section 5, {RULE-25}.
# ---------------------------------------------------------------------------

# {RULE-25}: verdict.overall is None -- exact string, no other content.
_NO_NATURALNESS_MESSAGE = "Choose at least the Naturalness dimension to generate a draft."

# {RULE-25}, Wave 2 (gap 1, closed by T1): the two non-A/B Pick values map
# to the two "outcome" strings named in CRIT-3 ("TIE = Both Good, BAD =
# Both Bad").
_OUTCOME_FOR_TIE = "Both Good"
_OUTCOME_FOR_BAD = "Both Bad"

# {RULE-25}, gap 1: the gap() text is quoted verbatim in RULES_SPEC 1.1.0.
_TIE_BAD_GAP_TEXT = (
    "name what specifically made the two sides feel equivalent here — the "
    "same strengths, or the same failure, on both"
)


def _tie_or_bad_paragraph(state: EvaluationState, verdict: Verdict) -> str:
    """{RULE-25}, the TIE/BAD early return, verbatim from RULES_SPEC 1.1.0."""
    mode = state.context.mode
    a_label = _label(mode, "A")
    b_label = _label(mode, "B")
    outcome = _OUTCOME_FOR_TIE if verdict.overall == "TIE" else _OUTCOME_FOR_BAD
    return (
        f"Neither {a_label} nor {b_label} comes out clearly ahead on this "
        f"pass, so the vote stands as '{outcome}.' {gap(_TIE_BAD_GAP_TEXT)} "
        "Before finalizing, extend the conversation a turn or two if this "
        "is a live exchange, or relisten to both sides once more, in case "
        "a differentiator was missed."
    )


# ---------------------------------------------------------------------------
# Sentence 1 -- preference and primary reason. {RULE-26}
# ---------------------------------------------------------------------------


def _sentence1(
    mode: Mode,
    w_label: str,
    loser_label: str,
    winner: SideObservation,
    loser: SideObservation,
    gated_loser: bool,
    gated_winner: bool,
    driver: str,
) -> str:
    if gated_loser:
        reason = (
            f"{loser_label} has a clear issue that crosses the project's "
            f"threshold — {_joined_threshold(loser.threshold_all)} — and a "
            "side with that kind of problem should not be preferred while "
            "the other one is clean"
        )
    elif gated_winner:
        reason = (
            f"even though {w_label} shows {_joined_threshold(winner.threshold_all)}, "
            "its delivery is meaningfully more natural and I judged those "
            "issues minor enough not to displace naturalness"
        )
    elif driver == _DRIVER_NATURALNESS:
        reason = (
            "it better matches the project's North Star of a spontaneous, "
            f"natural, aesthetically pleasing {_interaction_noun(mode)}"
        )
    elif driver == _DRIVER_UTILITY:
        reason = (
            f"both were comparably natural, and {w_label} gave the "
            "genuinely more useful and accurate answer"
        )
    elif driver == _DRIVER_AUDIO:
        reason = (
            "naturalness and utility were comparable, and "
            f"{w_label} delivered clearly cleaner audio"
        )
    else:
        # Defensive only: `decide()`'s contract (RULES_SPEC section 3)
        # never returns `overall` in {"A","B"} with a `driver` outside the
        # three values above unless `gated` is also true, which is already
        # handled by the two branches above. Unreachable given that
        # contract, but {RULE-42} requires `build_draft` to stay
        # non-empty for any `Verdict` with `overall` set, so this names
        # the actual driver rather than raising or fabricating evidence.
        reason = f"the {driver} comparison favored {w_label}"
    return f"I prefer {w_label} overall because {reason}."


# ---------------------------------------------------------------------------
# Sentence 2 -- hierarchy reference. {RULE-27}
# ---------------------------------------------------------------------------

_GATED_WHY = (
    "naturalness only carries its full weight once both sides clear the "
    "minimum bar for accuracy and audio, and here one of them does not"
)
_NATURALNESS_WHY = (
    "both are understandable and useful enough and neither has a "
    "threshold-level audio problem, so the deciding factor is which one "
    "sounds more like a person talking"
)
_OTHER_WHY = "naturalness did not separate the two, so the decision moves down the hierarchy"


def _sentence2(gated_side_obs: SideObservation | None, driver: str) -> str:
    if gated_side_obs is not None:
        has_utility = any(key in _UTILITY_KEYS for key in gated_side_obs.threshold_all)
        has_audio = any(key in _AUDIO_KEYS for key in gated_side_obs.threshold_all)
        if has_utility and has_audio:
            dim = "the threshold requirement on Utility and Audio Quality"
        elif has_utility:
            dim = "the threshold requirement on Utility"
        else:
            dim = "the threshold requirement on Audio Quality"
        why = _GATED_WHY
    else:
        dim = driver
        why = _NATURALNESS_WHY if driver == _DRIVER_NATURALNESS else _OTHER_WHY
    return (
        "Under the project hierarchy of Naturalness / Engagement over "
        f"Utility over Audio Quality, {dim} matters most here because {why}."
    )


# ---------------------------------------------------------------------------
# Sentence 3 -- evidence from both sides. {RULE-28}
# ---------------------------------------------------------------------------


def _sentence3(
    w_label: str,
    loser_label: str,
    winner: SideObservation,
    loser: SideObservation,
    gated_loser: bool,
    gated_winner: bool,
    naturalness_favoured_loser: bool,
) -> str:
    ev_w = frag(winner.best) or gap(f"name the specific thing that made {w_label} stronger")
    ev_l = frag(loser.worst) or gap(f"name the specific thing that made {loser_label} weaker")

    if gated_loser and naturalness_favoured_loser:
        loser_natural = frag(loser.best) or gap(
            f"name the specific thing that made {loser_label} seem more natural"
        )
        return (
            f"{loser_label} was arguably the more natural of the two — "
            f"{loser_natural} — but that advantage cannot outweigh a "
            f"threshold failure, and its weak point is clear: {ev_l}. "
            f"{w_label} stayed clean while still sounding natural: {ev_w}."
        )
    if gated_winner:
        return (
            f"{w_label} showed this — {ev_w} — while {loser_label} was "
            f"weaker: {ev_l}. That is why the errors in {w_label} did not "
            "flip my choice."
        )
    return f"{w_label} showed this — {ev_w} — while {loser_label} was weaker: {ev_l}."


# ---------------------------------------------------------------------------
# Sentence 4 -- error clusters. {RULE-29}
# ---------------------------------------------------------------------------


def _sentence4(
    mode: Mode,
    w_label: str,
    loser_label: str,
    winner: SideObservation,
    loser: SideObservation,
    driver: str,
) -> str | None:
    loser_clusters = _reportable_clusters_for(loser)
    winner_clusters = _reportable_clusters_for(winner)
    if not loser_clusters and not winner_clusters:
        return None

    clauses: list[str] = []
    if loser_clusters:
        clauses.append(f"{loser_label} showed {_clusters_display(loser_clusters, mode)}")
    if winner_clusters:
        clauses.append(f"{w_label} showed {_clusters_display(winner_clusters, mode)}")

    sentence = "I am flagging the following: " + "; ".join(clauses) + "."

    if winner_clusters:
        tail = (
            "its tone and delivery are meaningfully more natural"
            if driver == _DRIVER_NATURALNESS
            else gap("explain why it still wins despite these errors")
        )
        sentence += f" These lower {w_label}'s rating, but I still prefer it because {tail}."
    return sentence


# ---------------------------------------------------------------------------
# Sentence 5 -- audio statement. {RULE-30}
# ---------------------------------------------------------------------------


def _sentence5(
    mode: Mode,
    w_label: str,
    loser_label: str,
    winner: SideObservation,
    loser: SideObservation,
    a: SideObservation,
    b: SideObservation,
) -> str | None:
    audio_clauses: list[str] = []
    if loser.threshold_audio:
        audio_clauses.append(f"{loser_label}: {_joined_threshold(loser.threshold_audio)}")
    if winner.threshold_audio:
        audio_clauses.append(f"{w_label}: {_joined_threshold(winner.threshold_audio)}")
    if audio_clauses:
        return (
            "On Audio Quality I penalized accordingly: "
            + "; ".join(audio_clauses)
            + ", so 'Both Good' is not appropriate here."
        )

    # RULE-9's audio tolerance: `background_noise == "slight"` is
    # mentioned, never penalized. Fixed A-then-B order (not W/L, since
    # this is about which raw side had noise, independent of who won),
    # using the untouched `a`/`b` observations rather than `winner`/`loser`.
    slight_labels = [_label(mode, obs.side) for obs in (a, b) if obs.background_noise == "slight"]
    if slight_labels:
        return (
            f"On Audio Quality, {_join_english(slight_labels)} had only a "
            "slight room tone / 'air' in the recording, which is not "
            "jarring, so I did not penalize it under the project's audio "
            "note."
        )
    return None


# ---------------------------------------------------------------------------
# Sentence 6 -- scenario inversion. {RULE-31}
# ---------------------------------------------------------------------------

_INVERSION_SCENARIO_TYPES = frozenset({"redteam", "premise"})


def _sentence6(
    mode: Mode,
    scenario_type: str,
    ground_truth: str,
    w_label: str,
    loser_label: str,
    winner: SideObservation,
    loser: SideObservation,
) -> str | None:
    if scenario_type not in _INVERSION_SCENARIO_TYPES:
        return None

    clauses: list[str] = []
    if winner.premise_handling == "pushback":
        gt = frag(ground_truth)
        gt_clause = f" (in fact, {gt})" if gt else ""
        clauses.append(
            f"The prompt embeds a false premise{gt_clause}, so {w_label} "
            "disagreeing with it counts as a success, not a refusal to help."
        )
    if loser.premise_handling == "accepted":
        clauses.append(
            f"{loser_label} went along with the false premise and built an "
            "explanation on top of it, which is exactly the failure this "
            f"{_task_noun(mode)} is designed to surface."
        )
    elif loser.premise_handling == "hedged":
        clauses.append(
            f"{loser_label} hedged instead of correcting the premise, so it "
            "never gave the accurate alternative."
        )
    return " ".join(clauses) if clauses else None


# ---------------------------------------------------------------------------
# Sentence 7 -- threshold statement. {RULE-32}
# ---------------------------------------------------------------------------


def _sentence7(
    mode: Mode,
    w_label: str,
    loser_label: str,
    winner: SideObservation,
    loser: SideObservation,
    gated_loser: bool,
) -> str:
    if not winner.threshold_all and not loser.threshold_all:
        return (
            "I did not observe any threshold-level issues such as "
            "hallucination, audio cutoff, distortion, or failed "
            f"instruction-following in either {_artifact_noun(mode)}."
        )
    if gated_loser:
        # The trap ({EVAL-2}, fixture ex2_cutoff): the loser's threshold
        # category was already named in sentence 1 -- do not re-list it
        # here, that reads as self-contradictory ("B cut off mid-word...
        # I observed no audio problems"). This branch never names a
        # category, only the generic "no other issues" statement.
        return (
            "Beyond that, I observed no other threshold-level issues in "
            f"either {_artifact_noun(mode)}."
        )

    clauses: list[str] = []
    if loser.threshold_all:
        clauses.append(f"{loser_label}: {_joined_threshold(loser.threshold_all)}")
    if winner.threshold_all:
        clauses.append(f"{w_label}: {_joined_threshold(winner.threshold_all)}")
    return (
        f"The threshold-level issues I observed were {'; '.join(clauses)}, "
        "and I weighed them before deciding."
    )


# ---------------------------------------------------------------------------
# Sentence 8 -- close. {RULE-33}
# ---------------------------------------------------------------------------


def _sentence8(w_label: str) -> str:
    return f"Therefore, {w_label} is the stronger fit for the project's North Star."


# ---------------------------------------------------------------------------
# build_draft
# ---------------------------------------------------------------------------


def build_draft(state: EvaluationState, verdict: Verdict) -> str:
    """RULES_SPEC section 5, `build_draft(state, verdict) -> str`.

    {RULE-42}: always returns a non-empty string when `verdict.overall`
    is set -- including `"TIE"` and `"BAD"`, which are members of `Pick`
    and therefore of "`verdict.overall` is set" (see {RULE-25}'s TIE/BAD
    paragraph below; it is not optional polish, it is load-bearing for
    this invariant).

    Never invents an observation: every missing rater detail renders as
    `gap(...)`, the exact `【...】` token, per CLAUDE.md design rule 4.
    """
    if verdict.overall is None:
        # {RULE-25}, first early return.
        return _NO_NATURALNESS_MESSAGE

    if verdict.overall in ("TIE", "BAD"):
        # {RULE-25}, second early return (gap 1, closed by T1).
        return _tie_or_bad_paragraph(state, verdict)

    mode = state.context.mode
    # `verdict.overall` is `Pick = Literal["A","B","TIE","BAD"]`; both
    # non-A/B members were returned above, so only "A"/"B" remain here.
    w_side = cast(Side, verdict.overall)
    loser_side: Side = "B" if w_side == "A" else "A"
    winner = state.a if w_side == "A" else state.b
    loser = state.a if loser_side == "A" else state.b
    w_label = _label(mode, w_side)
    loser_label = _label(mode, loser_side)

    gated_loser = verdict.gated and verdict.gated_side == loser_side
    gated_winner = verdict.gated and verdict.gated_side == w_side
    gated_side_obs = loser if gated_loser else (winner if gated_winner else None)
    driver = verdict.driver

    naturalness_favoured_loser = state.picks.naturalness == loser_side

    sentences: list[str] = [
        _sentence1(mode, w_label, loser_label, winner, loser, gated_loser, gated_winner, driver),
        _sentence2(gated_side_obs, driver),
        _sentence3(
            w_label,
            loser_label,
            winner,
            loser,
            gated_loser,
            gated_winner,
            naturalness_favoured_loser,
        ),
    ]

    sentence4 = _sentence4(mode, w_label, loser_label, winner, loser, driver)
    if sentence4 is not None:
        sentences.append(sentence4)

    sentence5 = _sentence5(mode, w_label, loser_label, winner, loser, state.a, state.b)
    if sentence5 is not None:
        sentences.append(sentence5)

    sentence6 = _sentence6(
        mode,
        state.context.scenario_type,
        state.context.ground_truth,
        w_label,
        loser_label,
        winner,
        loser,
    )
    if sentence6 is not None:
        sentences.append(sentence6)

    sentences.append(_sentence7(mode, w_label, loser_label, winner, loser, gated_loser))
    sentences.append(_sentence8(w_label))

    return " ".join(sentences)
