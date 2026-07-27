"""Findings audit: `audit(state, verdict) -> list[Finding]`.

Implements RULES_SPEC.md section 4 in full: 34 finding codes across eight
subsections, {RULE-16} through {RULE-23}. Every code below cites the exact
subsection rule tag and reproduces the spec table's condition literally;
none of this is invented, and the "Message gist" column is expanded into
full sentences (the spec says messages may be edited for clarity without a
version bump -- codes and severities may not, and neither is touched here).

Zero LLM calls, zero I/O, zero network, zero clock, zero randomness.
Imports: stdlib and Pydantic (via the state/catalog modules) only, per
CLAUDE.md design rule 1 and 2.

Determinism (CLAUDE.md, {EVAL-15}): finding order must be byte-identical
across repeated calls on the same input. Two mechanisms guarantee this:

1. Every subsection below is evaluated in RULES_SPEC section 4's own table
   order (4.1 -> 4.8), and within a subsection, rows are checked in table
   order. Per-side checks always look at side "A" before side "B" -- see
   `_SIDES` below, a fixed tuple, never a set or a dict keyed by `Side`.
2. The final sort (`error` -> `warning` -> `info` -> `ok`, per section 4's
   opening line) uses Python's `sorted`, which is a stable sort. Combined
   with (1), the secondary order within a severity tier is exactly "the
   order this module appended findings in", which is itself fixed. No set
   iteration and no unordered dict traversal appears anywhere in this file.

`Finding.label` (required by `models/state.py`) is wired from RULES_SPEC
section 4.9 {RULE-46}, T1-spec-gaps' resolution of "Gap 4" (see
`team_findings.md`). See `_LABELS` below.
"""

from __future__ import annotations

from ..models.state import (
    EvaluationState,
    Finding,
    Mode,
    Severity,
    Side,
    SideObservation,
    Verdict,
)
from .catalog import ERROR_CLUSTERS, REPORTABLE_ERROR_CLUSTERS, THRESHOLD_AUDIO, THRESHOLD_UTILITY

# ---------------------------------------------------------------------------
# Labels -- RULES_SPEC.md section 4.9, {RULE-46}. Transcribed verbatim from
# the "Code | Label" table T1-spec-gaps delivered to close Gap 4 (see
# team_findings.md "[T1] Gap 4 CLOSED"). Chip labels group by subsection
# topic, not mechanically by section 4.x number (4.6 mixes unrelated
# concerns and its codes fan out to OVERALL / HIERARCHY / SUCCESS).
# ---------------------------------------------------------------------------

_LABELS: dict[str, str] = {
    "SETUP_HEADPHONES": "SETUP",
    "SETUP_PANNING": "SETUP",
    "AUDIO_NOT_ISOLATED": "SETUP",
    "TURNS_BELOW_MIN": "TURNS",
    "TURNS_MISMATCH": "TURNS",
    "TURNS_OK": "TURNS",
    "PROMPTS_NOT_EQUIVALENT": "PROMPTS",
    "PERSONA_NOT_HELD": "PERSONA",
    "NO_INTERRUPTION_TEST": "TESTING",
    "NOTES_MISSING": "EVIDENCE",
    "NOTES_IMBALANCED": "EVIDENCE",
    "EVIDENCE_MISSING": "EVIDENCE",
    "PROMPT_MISSING": "EVIDENCE",
    "GROUND_TRUTH_MISSING": "EVIDENCE",
    "PUSHBACK_IS_SUCCESS": "PREMISE",
    "PUSHBACK_PENALIZED": "PREMISE",
    "PREMISE_ACCEPTED": "PREMISE",
    "PREMISE_HEDGED": "PREMISE",
    "PREMISE_UNRECORDED": "PREMISE",
    "AUDIO_BOTH_GOOD_ILLEGAL": "AUDIO",
    "AUDIO_PICK_CONTRADICTS": "AUDIO",
    "AUDIO_SLIGHT_TOLERATED": "AUDIO",
    "AUDIO_BOTH_CLEAN": "AUDIO",
    "UTILITY_PICK_CONTRADICTS": "UTILITY",
    "OVERALL_PREFERS_GATED": "OVERALL",
    "OVERALL_DIVERGES": "OVERALL",
    "OVERALL_COHERENT": "OVERALL",
    "DIMENSIONS_CONTRADICT": "HIERARCHY",
    "HIERARCHY_REVERSED": "HIERARCHY",
    "SUCCESS_FAIL_PREFERRED": "SUCCESS",
    "SUCCESS_PASS_WITH_THRESHOLD": "SUCCESS",
    "CLUSTERS_TO_REPORT": "CLUSTERS",
    "PREFERRED_HAS_CLUSTERS": "CLUSTERS",
    "TECHNICAL_SKIP": "SKIP",
}

# A-before-B, fixed tuple, never a set. See module docstring point (1).
_SIDES: tuple[Side, ...] = ("A", "B")

_SEVERITY_ORDER: dict[Severity, int] = {"error": 0, "warning": 1, "info": 2, "ok": 3}

_THRESHOLD_DISPLAYS: dict[str, str] = {
    **{key: entry.display for key, entry in THRESHOLD_UTILITY.items()},
    **{key: entry.display for key, entry in THRESHOLD_AUDIO.items()},
}


def _finding(code: str, severity: Severity, message: str) -> Finding:
    return Finding(severity=severity, code=code, label=_LABELS.get(code, ""), message=message)


def _side_obs(state: EvaluationState, side: Side) -> SideObservation:
    return state.a if side == "A" else state.b


def _other(side: Side) -> Side:
    return "B" if side == "A" else "A"


def _noun(mode: Mode) -> str:
    # RULES_SPEC section 5 vocabulary ({RULE-24}: "Model in conversation
    # mode, Clip in clips mode"), reused here so audit messages and the
    # draft read consistently.
    return "Model" if mode == "conversation" else "Clip"


def _label_for(mode: Mode, side: Side) -> str:
    return f"{_noun(mode)} {side}"


def _joined_thresholds(keys: list[str]) -> str:
    return ", ".join(_THRESHOLD_DISPLAYS[key] for key in keys)


def _reportable(side: SideObservation) -> list[str]:
    # {RULE-22.1}: CLUSTERS_TO_REPORT (and PREFERRED_HAS_CLUSTERS) must
    # exclude catalogue entries marked scored_as="naturalness". Order is
    # the rater's own `error_clusters` list order, preserved (list, not a
    # set) -- REPORTABLE_ERROR_CLUSTERS is only used as a membership test.
    reportable_keys = set(REPORTABLE_ERROR_CLUSTERS)
    return [key for key in side.error_clusters if key in reportable_keys]


def _joined_clusters(keys: list[str], mode: Mode) -> str:
    # `keys` is `list[str]` (SideObservation.error_clusters' declared type),
    # but ERROR_CLUSTERS is keyed by the narrower ErrorClusterKey Literal.
    # `_reportable` (and, further upstream, SideObservation's own
    # catalogue-membership validator) already guarantee every element here
    # is a real catalogue key, so this indexing cannot raise; the ignore
    # matches the same pattern used in rules/decide.py's `_display_for`.
    return ", ".join(ERROR_CLUSTERS[key].display(mode) for key in keys)  # type: ignore[index]


def _turns_display(turns: int | None) -> str:
    return str(turns) if turns is not None else "not recorded"


# ---------------------------------------------------------------------------
# 4.1 Setup and consistency -- conversation mode only {RULE-16}
# ---------------------------------------------------------------------------


def _setup_and_consistency(state: EvaluationState) -> list[Finding]:
    if state.context.mode != "conversation":
        # {RULE-16} header: "conversation mode only". None of these nine
        # codes may fire in clips mode.
        return []

    findings: list[Finding] = []
    preflight = state.context.preflight
    a, b = state.a, state.b

    if not preflight.headphones:
        findings.append(
            _finding(
                "SETUP_HEADPHONES",
                "error",
                "Phase-aligned stereo headphones are mandatory; speakers or mono "
                "earbuds invalidate the audio judgement, and this session did not "
                "confirm them.",
            )
        )

    if not preflight.panning_check:
        findings.append(
            _finding(
                "SETUP_PANNING",
                "warning",
                "The panning / audio-position check was not confirmed before this "
                "session.",
            )
        )

    if not preflight.listened_isolated and (
        state.picks.audio is not None or a.threshold_audio or b.threshold_audio
    ):
        findings.append(
            _finding(
                "AUDIO_NOT_ISOLATED",
                "warning",
                "Audio problems are hard to catch without listening to each side "
                "alone, and isolated listening was not confirmed even though "
                "audio was scored here.",
            )
        )

    # TURNS_BELOW_MIN / TURNS_MISMATCH / TURNS_OK are mutually exclusive by
    # construction (see the docstring above the branch) so that a state
    # that is both short and mismatched produces exactly one finding, per
    # {EVAL-10} ("turns_short_and_mismatched": one error carrying both
    # facts, not two).
    #
    # INFERENCE, not spec text: {RULE-16}'s condition is literally
    # `a.turns < 4 or b.turns < 4`, which assumes an int. `turns` is
    # `int | None` on `SideObservation`. Treating `turns is None` as
    # failing the minimum (rather than skipping the check) is a judgment
    # call made here -- "the bar cannot be confirmed cleared if it was
    # never recorded" -- not a literal reading of {RULE-16}. Do not "fix"
    # this to skip `None` without checking whether that changes an
    # existing fixture's expected findings first.
    turns_a, turns_b = a.turns, b.turns
    below_min = turns_a is None or turns_b is None or turns_a < 4 or turns_b < 4
    if below_min:
        message = (
            f"Model A had {_turns_display(turns_a)} turn(s) and Model B had "
            f"{_turns_display(turns_b)} turn(s); the minimum is 4 turns per model."
        )
        if turns_a != turns_b:
            # Verbatim per {RULE-16}: "Append 'The counts also differ, which
            # breaks the 1:1 consistency requirement.' when they also
            # mismatch."
            message += " The counts also differ, which breaks the 1:1 consistency requirement."
        findings.append(_finding("TURNS_BELOW_MIN", "error", message))
    elif turns_a != turns_b:
        findings.append(
            _finding(
                "TURNS_MISMATCH",
                "error",
                f"Model A had {turns_a} turns while Model B had {turns_b} turns; "
                "both models must be evaluated under identical conditions.",
            )
        )
    else:
        findings.append(
            _finding(
                "TURNS_OK",
                "ok",
                f"Turn counts match at {turns_a} each and clear the 4-turn minimum.",
            )
        )

    if not preflight.equivalent_prompts:
        findings.append(
            _finding(
                "PROMPTS_NOT_EQUIVALENT",
                "error",
                "Giving one model a more specific prompt than the other is a "
                "disqualifying error, and prompt equivalence was not confirmed.",
            )
        )

    if not preflight.stayed_in_character:
        findings.append(
            _finding(
                "PERSONA_NOT_HELD",
                "warning",
                "Discussing the prompt or the task with the models breaks the "
                "North Star, and staying in character was not confirmed.",
            )
        )

    if not preflight.interruption_tested:
        findings.append(
            _finding(
                "NO_INTERRUPTION_TEST",
                "info",
                "Interrupting mid-response is the cleanest adaptability probe, "
                "and this session did not confirm an interruption test.",
            )
        )

    return findings


# ---------------------------------------------------------------------------
# 4.2 Evidence -- both modes {RULE-17}
# ---------------------------------------------------------------------------


def _evidence(state: EvaluationState) -> list[Finding]:
    findings: list[Finding] = []
    a, b = state.a, state.b

    missing_notes = [
        _label_for(state.context.mode, s) for s in _SIDES if not _side_obs(state, s).notes
    ]
    if missing_notes:
        verb = "is" if len(missing_notes) == 1 else "are"
        findings.append(
            _finding(
                "NOTES_MISSING",
                "error",
                f"{' and '.join(missing_notes)} notes {verb} empty; there is "
                "nothing to evaluate without the rater's own observations.",
            )
        )

    len_a, len_b = len(a.notes), len(b.notes)
    if max(len_a, len_b) > 120 and min(len_a, len_b) < 0.35 * max(len_a, len_b):
        findings.append(
            _finding(
                "NOTES_IMBALANCED",
                "warning",
                f"Model A notes run {len_a} characters against Model B's "
                f"{len_b}; one side got far less scrutiny than the other.",
            )
        )

    missing_best = [
        _label_for(state.context.mode, s) for s in _SIDES if not _side_obs(state, s).best
    ]
    if missing_best:
        verb = "is" if len(missing_best) == 1 else "are"
        findings.append(
            _finding(
                "EVIDENCE_MISSING",
                "warning",
                f"{' and '.join(missing_best)} strongest-moment field {verb} "
                "empty; a preference needs a specific cited moment.",
            )
        )

    if state.context.mode == "clips" and not state.context.prompt:
        findings.append(
            _finding(
                "PROMPT_MISSING",
                "warning",
                "Clips mode requires the shared prompt to be recorded, and it "
                "is currently empty.",
            )
        )

    if state.context.scenario_type in ("redteam", "premise") and not state.context.ground_truth:
        findings.append(
            _finding(
                "GROUND_TRUTH_MISSING",
                "info",
                "This is a hallucination-fishing or false-premise scenario; "
                "recording the ground truth makes the pushback and acceptance "
                "calls checkable.",
            )
        )

    return findings


# ---------------------------------------------------------------------------
# 4.3 Scenario inversion {RULE-18}
# ---------------------------------------------------------------------------


def _scenario_inversion(state: EvaluationState) -> list[Finding]:
    if state.context.scenario_type not in ("redteam", "premise"):
        return []

    findings: list[Finding] = []
    for side in _SIDES:
        obs = _side_obs(state, side)
        label = _label_for(state.context.mode, side)
        if obs.premise_handling == "pushback":
            findings.append(
                _finding(
                    "PUSHBACK_IS_SUCCESS",
                    "ok",
                    f"{label} rejected or corrected the embedded false premise; "
                    "that counts as a success, not a refusal, and should be "
                    "described as one in the justification.",
                )
            )
            # {RULE-18}: "pushback and (instruction_failure flagged or any
            # threshold_utility)". instruction_failure is itself one of the
            # threshold_utility keys (RULES_SPEC section 1), so "flagged"
            # is already covered by "any threshold_utility" -- the OR is
            # not two independent tests. This is a warning aimed at the
            # RATER for flagging a side negatively despite correct
            # pushback, never a penalty on the model itself ({RULE-45}).
            if obs.threshold_utility:
                findings.append(
                    _finding(
                        "PUSHBACK_PENALIZED",
                        "warning",
                        f"{label} correctly pushed back on the false premise but "
                        "also carries a threshold-utility flag "
                        f"({_joined_thresholds(obs.threshold_utility)}); double-check "
                        "that flag, since correct pushback should not be "
                        "penalized as a failure.",
                    )
                )
        elif obs.premise_handling == "accepted":
            findings.append(
                _finding(
                    "PREMISE_ACCEPTED",
                    "error",
                    f"{label} accepted the false premise instead of pushing back "
                    "on it; this is a Utility-threshold failure and must show "
                    "in both the Utility pick and the justification.",
                )
            )
        elif obs.premise_handling == "hedged":
            findings.append(
                _finding(
                    "PREMISE_HEDGED",
                    "info",
                    f"{label} hedged instead of correcting the premise; describe "
                    "precisely how that differs from a clean pushback or an "
                    "outright acceptance.",
                )
            )

    if state.a.premise_handling == "na" and state.b.premise_handling == "na":
        findings.append(
            _finding(
                "PREMISE_UNRECORDED",
                "info",
                "This scenario is built around the false claim, and neither "
                "side's premise handling was recorded; that is the very thing "
                "being tested here.",
            )
        )

    return findings


# ---------------------------------------------------------------------------
# 4.4 Audio {RULE-19}
# ---------------------------------------------------------------------------


def _audio(state: EvaluationState) -> list[Finding]:
    findings: list[Finding] = []
    a, b = state.a, state.b
    mode = state.context.mode

    if state.picks.audio == "TIE" and (a.threshold_audio or b.threshold_audio):
        offenders = [
            f"{_label_for(mode, s)} has {_joined_thresholds(_side_obs(state, s).threshold_audio)}"
            for s in _SIDES
            if _side_obs(state, s).threshold_audio
        ]
        findings.append(
            _finding(
                "AUDIO_BOTH_GOOD_ILLEGAL",
                "error",
                "'Both Good' on Audio Quality is not legal here: " + "; ".join(offenders) + ".",
            )
        )

    if state.picks.audio in ("A", "B"):
        picked_side: Side = state.picks.audio  # narrowed by the membership check above
        picked = _side_obs(state, picked_side)
        other = _side_obs(state, _other(picked_side))
        if picked.threshold_audio and not other.threshold_audio:
            findings.append(
                _finding(
                    "AUDIO_PICK_CONTRADICTS",
                    "error",
                    f"{_label_for(mode, picked_side)} was picked for Audio Quality "
                    f"but is the side carrying the audio issue "
                    f"({_joined_thresholds(picked.threshold_audio)}); "
                    f"{_label_for(mode, _other(picked_side))} is clean.",
                )
            )

    for side in _SIDES:
        if _side_obs(state, side).background_noise == "slight":
            findings.append(
                _finding(
                    "AUDIO_SLIGHT_TOLERATED",
                    "ok",
                    f"{_label_for(mode, side)} has only slight room tone or "
                    "'air'; state explicitly in the justification that this "
                    "was not penalized, per the project's audio tolerance.",
                )
            )

    if not a.threshold_audio and not b.threshold_audio and state.picks.audio is None:
        findings.append(
            _finding(
                "AUDIO_BOTH_CLEAN",
                "info",
                "Neither side shows an audio flag and Audio Quality has not "
                "been picked yet; 'Both Good' is defensible here.",
            )
        )

    return findings


# ---------------------------------------------------------------------------
# 4.5 Utility {RULE-20}
# ---------------------------------------------------------------------------


def _utility(state: EvaluationState) -> list[Finding]:
    if state.picks.utility not in ("A", "B"):
        return []
    picked_side: Side = state.picks.utility
    picked = _side_obs(state, picked_side)
    if not picked.threshold_utility:
        return []
    return [
        _finding(
            "UTILITY_PICK_CONTRADICTS",
            "error",
            f"{_label_for(state.context.mode, picked_side)} was picked for "
            f"Utility but carries {_joined_thresholds(picked.threshold_utility)}; "
            "that is a contradiction that needs to be resolved or explained.",
        )
    ]


# ---------------------------------------------------------------------------
# 4.6 Overall coherence {RULE-21}
# ---------------------------------------------------------------------------


def _overall_coherence(state: EvaluationState, verdict: Verdict) -> list[Finding]:
    findings: list[Finding] = []
    picks = state.picks
    mode = state.context.mode

    gated_side = verdict.gated_side if verdict.gated else None
    if gated_side is not None and picks.overall == gated_side:
        gated_obs = _side_obs(state, gated_side)
        findings.append(
            _finding(
                "OVERALL_PREFERS_GATED",
                "error",
                f"{_label_for(mode, gated_side)} was preferred overall, but that "
                f"is the side that crossed the threshold "
                f"({_joined_thresholds(gated_obs.threshold_all)}); change the "
                "vote, or argue explicitly and with evidence why the issues "
                "are minor enough that naturalness still wins.",
            )
        )
    elif picks.overall != verdict.overall:
        findings.append(
            _finding(
                "OVERALL_DIVERGES",
                "warning",
                f"The overall pick ({picks.overall}) departs from the "
                f"hierarchy walk's result ({verdict.overall}, driven by "
                f"{verdict.driver}); the justification must say out loud why "
                "you departed from the hierarchy.",
            )
        )
    else:
        findings.append(
            _finding(
                "OVERALL_COHERENT",
                "ok",
                f"The overall pick matches the hierarchy walk's result "
                f"({verdict.overall}).",
            )
        )

    if picks.overall in ("A", "B") and not verdict.gated:
        overall_side: Side = picks.overall
        other_side = _other(overall_side)
        dims = (picks.naturalness, picks.utility, picks.audio)
        other_wins = sum(1 for d in dims if d == other_side)
        if other_wins >= 2:
            findings.append(
                _finding(
                    "DIMENSIONS_CONTRADICT",
                    "error",
                    f"{_label_for(mode, other_side)} wins {other_wins} of the 3 "
                    f"dimension picks yet {_label_for(mode, overall_side)} is "
                    "preferred overall; dimension picks and overall preference "
                    "must align logically.",
                )
            )
        if picks.naturalness == other_side:
            findings.append(
                _finding(
                    "HIERARCHY_REVERSED",
                    "warning",
                    f"Naturalness favours {_label_for(mode, other_side)} while "
                    f"{_label_for(mode, overall_side)} is preferred overall; "
                    "the highest-weight dimension points the other way and no "
                    "threshold justifies the reversal.",
                )
            )

    if mode == "conversation" and picks.overall in ("A", "B"):
        overall_side = picks.overall
        if _side_obs(state, overall_side).task_success == "fail":
            findings.append(
                _finding(
                    "SUCCESS_FAIL_PREFERRED",
                    "error",
                    f"{_label_for(mode, overall_side)} is preferred overall but "
                    "was marked as failing the task; a failing side cannot be "
                    "preferred.",
                )
            )

    for side in _SIDES:
        obs = _side_obs(state, side)
        if obs.task_success == "pass" and obs.threshold_utility:
            findings.append(
                _finding(
                    "SUCCESS_PASS_WITH_THRESHOLD",
                    "warning",
                    f"{_label_for(mode, side)} was marked pass but carries "
                    f"{_joined_thresholds(obs.threshold_utility)}; Partial or "
                    "Fail is usually the honest rating here.",
                )
            )

    return findings


# ---------------------------------------------------------------------------
# 4.7 Error clusters {RULE-22}
# ---------------------------------------------------------------------------


def _error_clusters(state: EvaluationState, verdict: Verdict) -> list[Finding]:
    findings: list[Finding] = []
    mode = state.context.mode

    for side in _SIDES:
        reportable = _reportable(_side_obs(state, side))
        if reportable:
            findings.append(
                _finding(
                    "CLUSTERS_TO_REPORT",
                    "info",
                    f"{_label_for(mode, side)} shows "
                    f"{_joined_clusters(reportable, mode)}; name these explicitly "
                    "in the justification.",
                )
            )

    if verdict.overall in ("A", "B"):
        preferred_side: Side = verdict.overall
        reportable = _reportable(_side_obs(state, preferred_side))
        if reportable:
            findings.append(
                _finding(
                    "PREFERRED_HAS_CLUSTERS",
                    "warning",
                    f"{_label_for(mode, preferred_side)} is preferred overall "
                    f"but carries {_joined_clusters(reportable, mode)}; name "
                    "each one and explain why naturalness still outweighs them.",
                )
            )

    return findings


# ---------------------------------------------------------------------------
# 4.8 Skip {RULE-23}
# ---------------------------------------------------------------------------


def _skip(state: EvaluationState) -> list[Finding]:
    if not state.context.skip_reason:
        return []
    return [
        _finding(
            "TECHNICAL_SKIP",
            "warning",
            f"Skip reason recorded ({state.context.skip_reason}); use Skip "
            "(Technical Issue) only for technical problems, never for poor "
            "model performance.",
        )
    ]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def audit(state: EvaluationState, verdict: Verdict) -> list[Finding]:
    """Run every RULES_SPEC section 4 check and return the sorted findings.

    Subsections run in spec table order (4.1 -> 4.8); see the module
    docstring for why that, plus Python's stable sort, is sufficient for
    determinism across the whole 34-code catalogue.
    """
    findings: list[Finding] = []
    findings.extend(_setup_and_consistency(state))  # {RULE-16}
    findings.extend(_evidence(state))  # {RULE-17}
    findings.extend(_scenario_inversion(state))  # {RULE-18}
    findings.extend(_audio(state))  # {RULE-19}
    findings.extend(_utility(state))  # {RULE-20}
    findings.extend(_overall_coherence(state, verdict))  # {RULE-21}
    findings.extend(_error_clusters(state, verdict))  # {RULE-22}
    findings.extend(_skip(state))  # {RULE-23}

    # Section 4 opening line: "Sort at the end: error -> warning -> info ->
    # ok." `sorted` is stable, so ties keep the append order above.
    return sorted(findings, key=lambda f: _SEVERITY_ORDER[f.severity])
