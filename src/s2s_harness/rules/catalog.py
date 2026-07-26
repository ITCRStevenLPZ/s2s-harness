"""Rules catalogues: the closed vocabulary of error clusters and threshold breaches.

Implements RULES_SPEC {RULE-1} (error clusters), {RULE-2} (scored_as
carve-out), {RULE-3} (threshold utility), {RULE-4} (threshold audio), and
the derivation notes referenced from {RULE-5}/{RULE-6}/{RULE-9} inline
below, wherever `normalize` (a later phase) will add a derived key.

Transcribed verbatim from `docs/RULES_SPEC.md` section 1 ("Catalogues") and
cross-checked against `criteria/project-criteria.md` ("Error clusters",
"Threshold breaches", "Audio tolerance"). Every key, display string, mode
assignment and `derived` flag below traces to those two documents by
inline comment. Changing a rule means changing
`criteria/project-criteria.md` first, in the same commit as this file, per
CLAUDE.md design rule 5 — nothing here is invented.

Zero LLM calls, zero I/O, zero network, zero clock, zero randomness.
Imports: stdlib and Pydantic only, per CLAUDE.md design rule 1 and 2.

Display strings are noun phrases that splice cleanly into a sentence such
as `"Clip B had {display}"` (RULES_SPEC section 1, opening paragraph).
That splice is the literal BUILD_PLAN Phase 1 acceptance check. Verdict:
16 of 18 catalogue entries PASS it. `interrupts_user` and
`ignores_interruption` FAIL it -- both are bare gerund-clause phrasings
("interrupting me or talking over my turn", "ignoring my attempts to
interrupt or correct it") and "{Side} had {gerund clause}" is not
grammatical English, unlike every other entry's noun-phrase form. This is
transcribed verbatim from RULES_SPEC, not a bug in this module; the fix
belongs in a RULES_SPEC wording revision via `criteria-keeper`, not a
silent reword here. Full splice table and per-entry verdicts:
`team_findings.md`, "[T2] Definitive splice verdicts, all 18 entries".
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

# GRAPH_SPEC section 1: Mode = Literal["conversation", "clips"]. Redefined
# here (not imported) because rules/ is the foundation layer — models/
# depends on this catalogue's key names for its own validators, not the
# other way around.
Mode = Literal["conversation", "clips"]

ErrorClusterKey = Literal[
    "repetitive",
    "degradation",
    "awkward_silence",
    "embodied",
    "speech_recognition",
    "interrupts_user",
    "ignores_interruption",
    "robotic_intonation",
    "over_structured",
]

ThresholdUtilityKey = Literal[
    "hallucination",
    "false_premise",
    "instruction_failure",
    "premise_redteam",
]

ThresholdAudioKey = Literal[
    "cutoff",
    "clicks",
    "distortion",
    "dropout",
    "notable_noise",
]


class ErrorClusterEntry(BaseModel):
    """One row of RULES_SPEC section 1, "Error clusters -- shared" table.

    `display_conversation` and `display_clips` are stored as two already
    -reconstructed strings rather than the raw " / "-joined cell from the
    spec table, so a caller picks the correct form with `.display(mode)`
    instead of splitting a string at render time. For a key whose `modes`
    excludes a form (for example `speech_recognition` is conversation
    -only), the unused field is set equal to the used one; it is never
    read because callers must consult `modes` (or a mode profile) before
    rendering, per RULES_SPEC section 6 and GRAPH_SPEC section 5.
    """

    model_config = ConfigDict(frozen=True)

    key: ErrorClusterKey
    display_conversation: str
    display_clips: str
    modes: tuple[Mode, ...]
    # RULES_SPEC section 1 note: robotic_intonation and over_structured are
    # not official error clusters, they are Naturalness evidence. This is
    # the ONLY field that distinguishes them; no other entry sets it.
    scored_as: Literal["naturalness"] | None = None

    def display(self, mode: Mode) -> str:
        """Return the display string for the requested mode."""
        return self.display_conversation if mode == "conversation" else self.display_clips


class ThresholdEntry(BaseModel):
    """One row of a threshold catalogue (utility or audio).

    Threshold tables in RULES_SPEC section 1 carry no Modes column — both
    breach lists apply identically in conversation and clips mode
    (criteria/project-criteria.md "Threshold breaches" is mode-agnostic
    too), so there is a single `display`, not a per-mode pair.
    """

    model_config = ConfigDict(frozen=True)

    key: str
    display: str
    # True for the two entries RULES_SPEC section 2 adds to a side's
    # threshold list itself (`normalize`) rather than the rater setting
    # them directly. GRAPH_SPEC section 1: "derived by `normalize`, never
    # set by the caller."
    derived: bool = False


# ---------------------------------------------------------------------------
# Error clusters -- RULES_SPEC section 1, "Error clusters -- shared" table.
# Dict insertion order matches the spec table top to bottom. Any code that
# iterates ERROR_CLUSTERS (for example building CLUSTERS_TO_REPORT text)
# must rely on this order and must never re-sort through a set or an
# unordered dict, per CLAUDE.md's determinism rule.
# ---------------------------------------------------------------------------

ERROR_CLUSTERS: dict[ErrorClusterKey, ErrorClusterEntry] = {
    "repetitive": ErrorClusterEntry(
        key="repetitive",
        # RULES_SPEC section 1: "repetitive phrasing across turns / inside
        # the response", modes: both. The shared head "repetitive
        # phrasing" is written out in full for each mode instead of
        # storing the bare tail fragment "inside the response".
        display_conversation="repetitive phrasing across turns",
        display_clips="repetitive phrasing inside the response",
        modes=("conversation", "clips"),
    ),
    "degradation": ErrorClusterEntry(
        key="degradation",
        # RULES_SPEC section 1: "noticeable degradation as the
        # conversation continued / a response that fell apart as it went
        # on", modes: both.
        display_conversation="noticeable degradation as the conversation continued",
        display_clips="a response that fell apart as it went on",
        modes=("conversation", "clips"),
    ),
    "awkward_silence": ErrorClusterEntry(
        key="awkward_silence",
        # RULES_SPEC section 1: "awkward silences / a long, awkward
        # silence", modes: both.
        display_conversation="awkward silences",
        display_clips="a long, awkward silence",
        modes=("conversation", "clips"),
    ),
    "embodied": ErrorClusterEntry(
        key="embodied",
        # RULES_SPEC section 1: "an embodied-experience claim", modes:
        # both, one form. criteria/project-criteria.md "Error clusters":
        # "References to embodied experiences -- a digital AI offering to
        # do something requiring a physical body."
        display_conversation="an embodied-experience claim",
        display_clips="an embodied-experience claim",
        modes=("conversation", "clips"),
    ),
    "speech_recognition": ErrorClusterEntry(
        key="speech_recognition",
        # RULES_SPEC section 1: "speech-recognition failures", modes:
        # conversation.
        display_conversation="speech-recognition failures",
        display_clips="speech-recognition failures",  # unused: modes excludes clips
        modes=("conversation",),
    ),
    "interrupts_user": ErrorClusterEntry(
        key="interrupts_user",
        # RULES_SPEC section 1: "interrupting me / talking over my turn",
        # modes: conversation. Unlike the three both-mode entries above,
        # this key has no clip counterpart -- clips mode replaces
        # interruption clusters with robotic_intonation/over_structured
        # entirely (GRAPH_SPEC section 5, "Interruption-related
        # clusters"). The "/" here is therefore not a mode split; both
        # source fragments describe the same conversation-only behavior
        # and are joined with "or" so neither is silently dropped, the
        # same pattern used for the threshold_utility "hallucination"
        # entry below.
        display_conversation="interrupting me or talking over my turn",
        display_clips="interrupting me or talking over my turn",  # unused: modes excludes clips
        modes=("conversation",),
    ),
    "ignores_interruption": ErrorClusterEntry(
        key="ignores_interruption",
        # RULES_SPEC section 1: "ignoring my attempts to interrupt or
        # correct it", modes: conversation, one form already.
        display_conversation="ignoring my attempts to interrupt or correct it",
        display_clips="ignoring my attempts to interrupt or correct it",  # unused
        modes=("conversation",),
    ),
    "robotic_intonation": ErrorClusterEntry(
        key="robotic_intonation",
        # RULES_SPEC section 1: "robotic intonation and unnatural rhythm",
        # modes: clips. NOT an official error cluster -- Naturalness
        # evidence. criteria/project-criteria.md "Error clusters" closing
        # paragraph: "Robotic intonation and over-structured
        # assistant-style delivery are not clusters. They are Naturalness
        # evidence and are scored inside that dimension."
        display_conversation="robotic intonation and unnatural rhythm",  # unused: clips only
        display_clips="robotic intonation and unnatural rhythm",
        modes=("clips",),
        scored_as="naturalness",
    ),
    "over_structured": ErrorClusterEntry(
        key="over_structured",
        # RULES_SPEC section 1: "an over-structured, assistant-style
        # delivery", modes: clips. Same Naturalness carve-out as above.
        display_conversation="an over-structured, assistant-style delivery",  # unused
        display_clips="an over-structured, assistant-style delivery",
        modes=("clips",),
        scored_as="naturalness",
    ),
}

# ---------------------------------------------------------------------------
# Threshold -- utility. RULES_SPEC section 1, "Threshold — utility" table.
# ---------------------------------------------------------------------------

THRESHOLD_UTILITY: dict[ThresholdUtilityKey, ThresholdEntry] = {
    "hallucination": ThresholdEntry(
        key="hallucination",
        # RULES_SPEC section 1: "hallucination / invented facts". No Modes
        # column exists for threshold tables, so the "/" is table
        # shorthand for "or", matching the un-abbreviated wording in
        # criteria/project-criteria.md "Threshold breaches", Utility side:
        # "hallucination or invented facts".
        display="hallucination or invented facts",
    ),
    "false_premise": ThresholdEntry(
        key="false_premise",
        # RULES_SPEC section 1: "acceptance of a false premise".
        display="acceptance of a false premise",
    ),
    "instruction_failure": ThresholdEntry(
        key="instruction_failure",
        # RULES_SPEC section 1: "failure to follow the instruction".
        display="failure to follow the instruction",
    ),
    "premise_redteam": ThresholdEntry(
        key="premise_redteam",
        # RULES_SPEC section 1: "acceptance of the false claim it was
        # supposed to challenge (derived, see section 2)". Added to
        # a/b.threshold_utility by `normalize` (RULES_SPEC section 2 rule
        # 2) when context.scenario_type is "redteam" or "premise" and
        # premise_handling == "accepted" and "false_premise" is not
        # already present -- never set directly by the rater.
        display="acceptance of the false claim it was supposed to challenge",
        derived=True,
    ),
}

# ---------------------------------------------------------------------------
# Threshold -- audio. RULES_SPEC section 1, "Threshold — audio" table.
# ---------------------------------------------------------------------------

THRESHOLD_AUDIO: dict[ThresholdAudioKey, ThresholdEntry] = {
    "cutoff": ThresholdEntry(
        key="cutoff",
        # RULES_SPEC section 1: "audio cut off mid-word".
        display="audio cut off mid-word",
    ),
    "clicks": ThresholdEntry(
        key="clicks",
        # RULES_SPEC section 1: "audible clicks or pops".
        display="audible clicks or pops",
    ),
    "distortion": ThresholdEntry(
        key="distortion",
        # RULES_SPEC section 1: "distortion or robotic artifacts".
        display="distortion or robotic artifacts",
    ),
    "dropout": ThresholdEntry(
        key="dropout",
        # RULES_SPEC section 1: "dropouts or lost audio".
        display="dropouts or lost audio",
    ),
    "notable_noise": ThresholdEntry(
        key="notable_noise",
        # RULES_SPEC section 1: "notable, distracting background noise
        # (derived, see section 2)". Added to a/b.threshold_audio by
        # `normalize` (RULES_SPEC section 2 rule 1) when
        # background_noise == "notable" -- never set directly by the
        # rater. "slight" adds nothing; that tolerance lives in
        # criteria/project-criteria.md "Audio tolerance" and must never
        # become a penalty (RULES_SPEC section 2, closing paragraph).
        display="notable, distracting background noise",
        derived=True,
    ),
}

# ---------------------------------------------------------------------------
# Convenience key tuples. Exposed so src/s2s_harness/models/state.py can
# validate flag keys against the catalogue (BUILD_PLAN Phase 2) without
# hardcoding the key lists a second time, which would itself be a magic
# -literal violation.
# ---------------------------------------------------------------------------

ERROR_CLUSTER_KEYS: tuple[ErrorClusterKey, ...] = tuple(ERROR_CLUSTERS.keys())
THRESHOLD_UTILITY_KEYS: tuple[ThresholdUtilityKey, ...] = tuple(THRESHOLD_UTILITY.keys())
THRESHOLD_AUDIO_KEYS: tuple[ThresholdAudioKey, ...] = tuple(THRESHOLD_AUDIO.keys())

# RULES_SPEC section 1 note + section 4.7: CLUSTERS_TO_REPORT "must exclude
# catalogue entries marked scored_as='naturalness'". Reportable clusters
# are the official project error-cluster list; robotic_intonation and
# over_structured are excluded here so the audit can never treat them as
# reportable errors.
REPORTABLE_ERROR_CLUSTERS: tuple[ErrorClusterKey, ...] = tuple(
    key for key, entry in ERROR_CLUSTERS.items() if entry.scored_as is None
)

# GRAPH_SPEC section 1: "derived by `normalize`, never set by the caller."
# These are the keys a validator must reject if they appear on an inbound
# (rater-supplied) SideObservation, since they only ever exist after
# `normalize` runs.
THRESHOLD_UTILITY_INPUT_KEYS: tuple[ThresholdUtilityKey, ...] = tuple(
    key for key, entry in THRESHOLD_UTILITY.items() if not entry.derived
)
THRESHOLD_AUDIO_INPUT_KEYS: tuple[ThresholdAudioKey, ...] = tuple(
    key for key, entry in THRESHOLD_AUDIO.items() if not entry.derived
)


class ModeProfile(BaseModel):
    """The catalogue entries visible to a given mode.

    GRAPH_SPEC section 5, "Mode differences": "Implement as two `catalog`
    profiles and two validator lists, selected by `context.mode`. Do not
    fork the engine." Threshold catalogues are identical in both modes;
    only the error-cluster set changes shape (interruption clusters swap
    for robotic_intonation/over_structured).
    """

    model_config = ConfigDict(frozen=True)

    mode: Mode
    error_clusters: tuple[ErrorClusterKey, ...]
    threshold_utility: tuple[ThresholdUtilityKey, ...]
    threshold_audio: tuple[ThresholdAudioKey, ...]


def _clusters_for(mode: Mode) -> tuple[ErrorClusterKey, ...]:
    return tuple(key for key, entry in ERROR_CLUSTERS.items() if mode in entry.modes)


CONVERSATION_PROFILE = ModeProfile(
    mode="conversation",
    error_clusters=_clusters_for("conversation"),
    threshold_utility=THRESHOLD_UTILITY_KEYS,
    threshold_audio=THRESHOLD_AUDIO_KEYS,
)

CLIPS_PROFILE = ModeProfile(
    mode="clips",
    error_clusters=_clusters_for("clips"),
    threshold_utility=THRESHOLD_UTILITY_KEYS,
    threshold_audio=THRESHOLD_AUDIO_KEYS,
)

MODE_PROFILES: dict[Mode, ModeProfile] = {
    "conversation": CONVERSATION_PROFILE,
    "clips": CLIPS_PROFILE,
}


def profile_for(mode: Mode) -> ModeProfile:
    """Return the catalogue profile for `mode`."""
    return MODE_PROFILES[mode]
