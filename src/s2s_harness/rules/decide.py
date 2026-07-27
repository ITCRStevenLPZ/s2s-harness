"""The threshold gate and the hierarchy walk.

Implements RULES_SPEC.md section 3, `decide(a, b, picks) -> Verdict`,
{RULE-10} through {RULE-15}.

Zero LLM calls, zero I/O, zero network, zero clock, zero randomness.
Imports: stdlib, Pydantic (via `models.state`) and `rules.catalog` only,
per CLAUDE.md design rules 1 and 2, and `docs/ARCHITECTURE.md`'s layer
table (`rules/` may import `models/`, never the reverse).

All trace strings below are transcribed verbatim from RULES_SPEC.md
section 3 (T1's Step 1 templates and the "Step 2 trace templates" block
that closed spec gaps 2 and 3, see `team_findings.md`), with one flagged
exception:

CONFLICT, not improvised (see `team_findings.md`, "[T3] CONFLICT
flagged... gap-2's `{pick}` vs `{RULE-41}` purity"): the spec defines
`{pick}` / `{A}` / `{B}` as "the full display of whichever side the
branch names (e.g. 'Model A' / 'Clip B')", which needs `TaskContext.mode`
-- an input `decide(a, b, picks) -> Verdict` does not take, and
`{RULE-41}` (section 7, same document) forbids reading anything beyond
`a.threshold_all`, `b.threshold_all` and `picks`. Resolved for this
deliverable by emitting the bare side letter ("A" / "B") everywhere the
template names a side. This is pending T1 ratification; every other word
of every trace string here is unchanged from the spec.
"""

from __future__ import annotations

from typing import Literal

from s2s_harness.models.state import Picks, Side, SideObservation, Verdict
from s2s_harness.rules import catalog

# RULES_SPEC section 1: the two closed catalogues that partition every key
# that can ever appear in `threshold_all`. Membership checks only (never
# iterated to build output text), so this does not run afoul of
# CLAUDE.md's "never iterate a set where output order matters" rule.
_UTILITY_KEYS: frozenset[str] = frozenset(catalog.THRESHOLD_UTILITY_KEYS)
_AUDIO_KEYS: frozenset[str] = frozenset(catalog.THRESHOLD_AUDIO_KEYS)

# Flattened str-keyed display lookups, derived once from the catalogue
# dicts. `catalog.THRESHOLD_UTILITY` / `THRESHOLD_AUDIO` are keyed by a
# narrow `Literal[...]` type for authoring safety inside `catalog.py`
# itself; `decide` receives plain `list[str]` (RULES_SPEC section 3 gives
# `threshold_all` no narrower type), so the lookup table here is
# deliberately widened to `dict[str, str]` at the boundary rather than
# threading `cast()` through every call site.
_UTILITY_DISPLAY: dict[str, str] = {
    key: entry.display for key, entry in catalog.THRESHOLD_UTILITY.items()
}
_AUDIO_DISPLAY: dict[str, str] = {
    key: entry.display for key, entry in catalog.THRESHOLD_AUDIO.items()
}

# RULES_SPEC section 3, `gate_name`. {RULE-14}
_GATE_NAME_BOTH = "Threshold — Utility & Audio Quality"
_GATE_NAME_UTILITY = "Threshold — Utility"
_GATE_NAME_AUDIO = "Threshold — Audio Quality"

# RULES_SPEC section 3, Step 2 driver strings. {RULE-15}
_DRIVER_NATURALNESS = "Naturalness / Engagement"
_DRIVER_NONE = "—"
_DRIVER_UTILITY = "Utility"
_DRIVER_AUDIO = "Audio Quality"
_DRIVER_NO_EVIDENCE = "No separating evidence"

# RULES_SPEC section 3, case both == 0. {RULE-13}. Verbatim.
_THRESHOLD_PASSED_TRACE = (
    "Threshold gate passed: neither side shows hallucination, false-premise "
    "acceptance, an instruction failure, or a jarring audio problem. "
    "Naturalness carries its full weight."
)


def gate_name(threshold_all: list[str]) -> str:
    """RULES_SPEC section 3, `gate_name`. {RULE-14}

    Maps a breaching side's flag mix to one of exactly three strings,
    determined by which of the two closed catalogues (utility, audio)
    contributed at least one key to `threshold_all`. Reads only the
    static catalogue membership and the caller-supplied key list, so it
    does not widen `decide`'s dependency surface beyond {RULE-41}.
    """
    has_utility = any(key in _UTILITY_KEYS for key in threshold_all)
    has_audio = any(key in _AUDIO_KEYS for key in threshold_all)
    if has_utility and has_audio:
        return _GATE_NAME_BOTH
    if has_utility:
        return _GATE_NAME_UTILITY
    return _GATE_NAME_AUDIO


def _display_for(key: str) -> str:
    """Look up a threshold key's display string in either catalogue.

    Both `SideObservation`'s validator and `rules.normalize` restrict
    `threshold_all` to keys drawn from `THRESHOLD_UTILITY` /
    `THRESHOLD_AUDIO`, so the fallback branch below is unreachable through
    the normal ingest path. It exists only so this function -- and
    therefore `decide` -- cannot raise on a hand-built, unvalidated
    `SideObservation` (`allow_derived_fields` reconstruction, a test
    fixture, etc.), preserving {RULE-40} even in that case.
    """
    utility_display = _UTILITY_DISPLAY.get(key)
    if utility_display is not None:
        return utility_display
    audio_display = _AUDIO_DISPLAY.get(key)
    if audio_display is not None:
        return audio_display
    return key


def _join_english(items: list[str]) -> str:
    """Render a list of display strings as one English clause.

    RULES_SPEC section 3, `joined(list)`. {RULE-47} -- added by T1 to
    close the gap this module surfaced mid-implementation, and confirmed
    identical to this function: single item as-is, two items "X and Y",
    three or more as an Oxford-comma list "X, Y, and Z".
    """
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _joined(threshold_all: list[str]) -> str:
    """`{joined ...}` as used in the RULE-10/RULE-11/RULE-12 templates.

    Preserves `threshold_all`'s existing order (utility keys first, per
    {RULE-7}) rather than sorting it.
    """
    return _join_english([_display_for(key) for key in threshold_all])


def _other(side: Side) -> Side:
    return "B" if side == "A" else "A"


def _gated_verdict(breach_side: Side, breach_all: list[str], picks: Picks) -> Verdict:
    """RULES_SPEC section 3, cases `thr_a > 0, thr_b == 0` and its mirror.

    {RULE-10} / {RULE-11}, verbatim trace text except for the `{A}`/`{B}`
    substitution -- see the module docstring's CONFLICT note: bare side
    letters are used here, not a mode-aware "Model A" / "Clip A" display,
    because `decide` has no `TaskContext` to read one from.
    """
    clean_side = _other(breach_side)
    joined = _joined(breach_all)
    trace = [
        f"Threshold gate: {breach_side} crosses the minimum threshold "
        f"({joined}); {clean_side} is clean. A side with misinformation, a "
        "jarring audio artifact or a major failure should not be preferred "
        "while the other one is clean."
    ]
    if picks.naturalness == breach_side:
        # {RULE-10}'s conditional extra trace line: naturalness and the
        # threshold pull in opposite directions.
        trace.append(
            f"{breach_side} is the more natural of the two, so naturalness "
            "and the threshold pull in opposite directions. Naturalness can "
            "still win only if those issues are minor and the rater argues "
            f"it explicitly with evidence. The default stays with {clean_side}."
        )
    return Verdict(
        overall=clean_side,
        driver=gate_name(breach_all),
        gated=True,
        gated_side=breach_side,
        trace=trace,
    )


def _both_breach_trace(a_threshold_all: list[str], b_threshold_all: list[str]) -> str:
    """{RULE-12}, both sides breach. Verbatim from RULES_SPEC section 3
    (gap 3, closed by T1), except for the `{A}`/`{B}` bare-letter
    substitution -- see the module docstring's CONFLICT note.
    """
    joined_a = _joined(a_threshold_all)
    joined_b = _joined(b_threshold_all)
    return (
        "Threshold gate: both A and B cross the minimum threshold — "
        f"A: {joined_a}; B: {joined_b}. Neither side clears the basic "
        "satisfaction bar on its own, so 'Both Bad' is defensible on the "
        "affected dimensions."
    )


def _hierarchy_walk(picks: Picks, trace: list[str]) -> Verdict:
    """RULES_SPEC section 3, Step 2. {RULE-15}

    `trace` already carries the Step 1 line(s) from the caller; each
    branch below appends exactly one more line before returning, per the
    spec's "each branch appends its own trace line." Trace text is
    verbatim from the "Step 2 trace templates" block (gap 2, closed by
    T1), except for the `{pick}` bare-letter substitution -- see the
    module docstring's CONFLICT note.
    """
    if picks.naturalness in ("A", "B"):
        trace.append(
            f"Hierarchy walk: {picks.naturalness} was picked for "
            "Naturalness / Engagement, the top of the project hierarchy, so "
            "that pick decides the vote without needing to weigh Utility or "
            "Audio Quality."
        )
        return Verdict(overall=picks.naturalness, driver=_DRIVER_NATURALNESS, trace=trace)

    if picks.naturalness is None:
        trace.append(
            "Hierarchy walk: no Naturalness / Engagement pick is recorded "
            "yet. That dimension carries the most weight in the project "
            "hierarchy and the vote cannot be decided without it — record a "
            "Naturalness pick before a verdict can be drawn."
        )
        return Verdict(overall=None, driver=_DRIVER_NONE, trace=trace)

    # picks.naturalness is "TIE" or "BAD" here: naturalness did not
    # separate the two sides, so the walk moves down the hierarchy.
    if picks.utility in ("A", "B"):
        trace.append(
            "Hierarchy walk: Naturalness / Engagement did not separate the "
            f"two sides, so the decision moves down to Utility. {picks.utility} "
            "was picked for Utility, and that pick decides the vote."
        )
        return Verdict(overall=picks.utility, driver=_DRIVER_UTILITY, trace=trace)

    if picks.audio in ("A", "B"):
        trace.append(
            "Hierarchy walk: neither Naturalness / Engagement nor Utility "
            "separated the two sides, so the decision moves to Audio "
            f"Quality, the last rung of the hierarchy. {picks.audio} was "
            "picked for Audio Quality, and that pick decides the vote."
        )
        return Verdict(overall=picks.audio, driver=_DRIVER_AUDIO, trace=trace)

    trace.append(
        "Hierarchy walk: Naturalness / Engagement, Utility and Audio "
        "Quality all failed to separate the two sides. Nothing in the "
        "record distinguishes them."
    )
    overall: Literal["BAD", "TIE"]
    if picks.naturalness == "BAD":
        trace.append("Naturalness itself was rated Both Bad, so the verdict follows suit.")
        overall = "BAD"
    else:
        trace.append(
            "Naturalness itself was rated Both Good with no other dimension "
            "breaking the tie, so the verdict is a tie."
        )
        overall = "TIE"
    return Verdict(overall=overall, driver=_DRIVER_NO_EVIDENCE, trace=trace)


def decide(a: SideObservation, b: SideObservation, picks: Picks) -> Verdict:
    """RULES_SPEC section 3, the full `decide` procedure. {RULE-10}..{RULE-15}

    {RULE-41}: this function reads only `a.threshold_all`,
    `b.threshold_all` and `picks` -- never `.notes`, `.turns`, `.mode`, or
    any other field on `a` / `b`, and it takes no `TaskContext` argument
    at all, so there is nothing else in scope to read by accident.

    {RULE-40}: this function never raises, for any input. There is no
    branch here that can throw -- no dict/list indexing without a
    default, no assertion, no external call -- for any combination of
    empty lists and `None` picks, including the fully empty state.
    """
    thr_a = len(a.threshold_all)
    thr_b = len(b.threshold_all)

    if thr_a > 0 and thr_b == 0:
        return _gated_verdict("A", a.threshold_all, picks)  # {RULE-10}
    if thr_b > 0 and thr_a == 0:
        return _gated_verdict("B", b.threshold_all, picks)  # {RULE-11}

    trace: list[str] = []
    if thr_a > 0 and thr_b > 0:
        trace.append(_both_breach_trace(a.threshold_all, b.threshold_all))  # {RULE-12}
    else:
        trace.append(_THRESHOLD_PASSED_TRACE)  # {RULE-13}

    return _hierarchy_walk(picks, trace)
