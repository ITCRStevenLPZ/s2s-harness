"""Bilingual signal detection: `scan(state) -> list[Suggestion]`.

Implements `docs/RULES_SPEC.md` section 6, {RULE-34} through {RULE-39},
against the Wave-2 (version 1.1.0) text that closed gap 6 -- the
`speech_recognition` scanner row and the two {RULE-35} tone-signal
pattern rows (see `team_findings.md`, "[T1] Gaps 1, 5, 6 CLOSED").

Zero LLM calls, zero I/O, zero network, zero clock, zero randomness.
Imports: stdlib (`re`), Pydantic (via `models.state`) and `rules.catalog`
only, per CLAUDE.md design rules 1 and 2, and `docs/ARCHITECTURE.md`'s
layer table (`rules/` may import `models/`, never the reverse).

The scanner suggests; it never sets a flag ({RULE-37}). `scan` reads
`a.notes` / `b.notes` and returns `Suggestion` objects; it does not
mutate `EvaluationState` at all. Accepting a suggestion (turning it into
a set flag on `SideObservation`) is an explicit caller action performed
elsewhere (CLI prompt, bridge click) -- never here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from s2s_harness.models.state import EvaluationState, Side, SideObservation, Suggestion
from s2s_harness.rules import catalog

# ---------------------------------------------------------------------------
# Scan table. RULES_SPEC section 6: "Each entry: (catalog_key, kind,
# pattern, label)." `label` is retained here purely as an internal,
# human-readable description of what the pattern denotes -- `Suggestion`
# (models/state.py, STATE-15) has no `label` field, so it is never
# propagated to output. It exists so a reader of this module can see what
# each pattern group means without cross-referencing RULES_SPEC section 6
# by hand.
# ---------------------------------------------------------------------------

SuggestionKind = str  # narrowed to Suggestion.kind's Literal at construction time


@dataclass(frozen=True)
class _ScanEntry:
    key: str
    kind: str  # one of Suggestion.kind's Literal members
    patterns: tuple[str, ...]
    label: str
    pattern: re.Pattern[str]


def _compile(patterns: tuple[str, ...]) -> re.Pattern[str]:
    """Case-insensitive alternation over literal fragments ({RULE-34}).

    Fragments are literal substrings (Spanish and English word/phrase
    fragments), not caller-facing regex -- each is escaped before being
    joined into the alternation so a fragment containing a regex
    metacharacter (an apostrophe is fine as-is; `re.escape` is applied
    uniformly so this stays true regardless of what future fragments look
    like) is matched literally, not interpreted as regex syntax.
    """
    return re.compile("|".join(re.escape(p) for p in patterns), re.IGNORECASE)


def _entry(key: str, kind: str, label: str, *patterns: str) -> _ScanEntry:
    return _ScanEntry(
        key=key, kind=kind, patterns=patterns, label=label, pattern=_compile(patterns)
    )


# RULES_SPEC section 6 table, {RULE-34}: 16 rows, one per error_cluster /
# threshold_utility / threshold_audio catalogue key, including
# `speech_recognition` (gap 6, closed by T1). Order matches the spec
# table top to bottom; iterated as a fixed tuple, never a set, so
# recomputing `scan` over the same notes always yields suggestions in the
# same order ({RULE-39}).
_ERROR_CLUSTER_ENTRIES: tuple[_ScanEntry, ...] = (
    _entry(
        "repetitive",
        "error_cluster",
        "repetitive phrasing across turns / inside the response",
        "repit",
        "repet",
        "repeat",
        "misma frase",
        "same phrase",
        "muletill",
        "over and over",
    ),
    _entry(
        "degradation",
        "error_cluster",
        "noticeable degradation as the conversation continued",
        "degrad",
        "empeor",
        "got worse",
        "se puso peor",
        "fell apart",
        "perdió el hilo",
        "rambl",
        "divag",
    ),
    _entry(
        "interrupts_user",
        "error_cluster",
        "interrupting me / talking over my turn",
        "interrump",
        "interrupt",
        "talked over",
        "habló encima",
        "me pisó",
        "no me dejó hablar",
    ),
    _entry(
        "ignores_interruption",
        "error_cluster",
        "ignoring my attempts to interrupt or correct it",
        "ignor",
        "no hizo caso",
        "kept going",
        "siguió hablando",
        "didn't stop",
        "no paró",
    ),
    _entry(
        "awkward_silence",
        "error_cluster",
        "awkward silences / a long, awkward silence",
        "silenc",
        "pausa larga",
        "dead air",
        "se quedó callad",
        "tardó en responder",
    ),
    _entry(
        "embodied",
        "error_cluster",
        "an embodied-experience claim",
        "café",
        "coffee",
        "agarr",
        "grab a",
        "físicamente",
        "tocar la puerta",
        "knock on",
        "te lo traigo",
        "ir a buscar",
    ),
    _entry(
        "robotic_intonation",
        "error_cluster",
        "robotic intonation and unnatural rhythm",
        "robótic",
        "monóton",
        "plano",
        "flat",
        "rígid",
        "stiff",
        "acartonad",
        "mecánic",
    ),
    _entry(
        "over_structured",
        "error_cluster",
        "an over-structured, assistant-style delivery",
        "estructurad",
        "lista",
        "bullet",
        "numerad",
        "asistente",
        "assistant-like",
        "enumera",
    ),
    _entry(
        "speech_recognition",
        "error_cluster",
        "speech-recognition failures",
        "no me entendió",
        "no entendió lo que dije",
        "reconocimiento de voz",
        "no captó",
        "se equivocó de palabra",
        "mishear",
        "misheard",
        "misrecognized",
        "didn't understand what I said",
        "voice recognition",
    ),
)

_THRESHOLD_UTILITY_ENTRIES: tuple[_ScanEntry, ...] = (
    _entry(
        "hallucination",
        "threshold_utility",
        "hallucination / invented facts",
        "alucin",
        "hallucin",
        "invent",
        "made up",
        "dato falso",
        "incorrect",
        "equivocad",
        "no es cierto",
    ),
    _entry(
        "false_premise",
        "threshold_utility",
        "acceptance of a false premise",
        "premisa",
        "false premise",
        "aceptó la",
        "went along",
        "siguió la corriente",
        "no corrigió",
        "se la crey",
    ),
    _entry(
        "instruction_failure",
        "threshold_utility",
        "failure to follow the instruction",
        "no siguió la instrucci",
        "refus",
        "se negó",
        "didn't follow",
        "no hizo lo que ped",
    ),
)

_THRESHOLD_AUDIO_ENTRIES: tuple[_ScanEntry, ...] = (
    _entry(
        "cutoff",
        "threshold_audio",
        "audio cut off mid-word",
        "cortó",
        "corte",
        "cut off",
        "se corta",
        "truncat",
        "a media palabra",
        "mid-word",
    ),
    _entry(
        "clicks",
        "threshold_audio",
        "audible clicks or pops",
        "click",
        "clic",
        "chasquid",
        "pop",
        "crackl",
        "estática",
        "static",
    ),
    _entry(
        "distortion",
        "threshold_audio",
        "distortion or robotic artifacts",
        "distorsi",
        "distort",
        "metálic",
        "artifact",
        "glitch",
        "garbl",
        "entrecortad",
    ),
    _entry(
        "dropout",
        "threshold_audio",
        "dropouts or lost audio",
        "dropout",
        "se perdió el audio",
        "lost audio",
        "audio se fue",
    ),
)

# RULES_SPEC section 6, {RULE-35}, Wave 2 (gap 6, closed by T1): two tone
# signals, advisory only, never a flag. `kind="tone"` per STATE-15.
# `key` values here are internal identifiers -- not RULES_SPEC section 1
# catalogue keys, since tone signals correspond to no closed-catalogue
# flag at all (that absence of a flag is the entire point of RULE-35).
_TONE_ENTRIES: tuple[_ScanEntry, ...] = (
    _entry(
        "warmth_naturalness_cue",
        "tone",
        "warmth/naturalness cue",
        "cálid",
        "warm",
        "cercan",
        "friendly",
        "like talking to a friend",
        "como hablar con un amigo",
        "genuin",
        "auténtic",
        "natural",
        "de verdad",
    ),
    _entry(
        "possible_slight_room_tone",
        "tone",
        "possible slight room tone",
        "room tone",
        "ruido de fondo leve",
        "leve ruido",
        "apenas se nota",
        "faint hiss",
        "un poco de eco",
        "barely audible",
        "aire de fondo",
        "slight background noise",
    ),
)

# Fixed order: error clusters, then threshold-utility, then
# threshold-audio, then tone signals -- the same subsection order as
# RULES_SPEC section 6's table plus its trailing tone-signal sub-table.
_SCAN_TABLE: tuple[_ScanEntry, ...] = (
    _ERROR_CLUSTER_ENTRIES + _THRESHOLD_UTILITY_ENTRIES + _THRESHOLD_AUDIO_ENTRIES + _TONE_ENTRIES
)

_SIDES: tuple[Side, ...] = ("A", "B")


def _flag_already_set(entry: _ScanEntry, side_obs: SideObservation) -> bool:
    """{RULE-36}: "a suggestion is produced only when the corresponding
    flag is currently unset." Tone signals ({RULE-35}) correspond to no
    flag at all -- there is nothing to check, so they are always eligible
    once matched.
    """
    if entry.kind == "error_cluster":
        return entry.key in side_obs.error_clusters
    if entry.kind == "threshold_utility":
        return entry.key in side_obs.threshold_utility
    if entry.kind == "threshold_audio":
        return entry.key in side_obs.threshold_audio
    return False  # kind == "tone"


def _mode_allows(entry: _ScanEntry, mode: str) -> bool:
    """Error-cluster catalogue keys are mode-scoped (RULES_SPEC section 1
    `Modes` column): `speech_recognition` / `interrupts_user` /
    `ignores_interruption` are conversation-only, `robotic_intonation` /
    `over_structured` are clips-only. Suggesting a flag that is not even
    part of the current mode's profile would hand the caller a
    `Suggestion.target` that `SideObservation`'s own validator rejects if
    ever accepted -- so the scanner respects the same `modes` tuple
    `rules/catalog.py` already defines, rather than re-deriving it.
    Threshold catalogues and tone signals are mode-agnostic (no `Modes`
    column in section 1's threshold tables; RULE-35 does not scope tone
    signals to a mode either).
    """
    if entry.kind != "error_cluster":
        return True
    # `entry.key` is a plain `str` (the dataclass field type), not the
    # catalogue's narrower `Literal` key type, so `.get()` cannot resolve
    # to a single overload -- `call-overload` is the real error `mypy`
    # reports here, not `arg-type`.
    cluster_entry = catalog.ERROR_CLUSTERS.get(entry.key)  # type: ignore[call-overload]
    if cluster_entry is None:
        return True
    return mode in cluster_entry.modes


def scan(state: EvaluationState) -> list[Suggestion]:
    """RULES_SPEC section 6, `scan(state) -> list[Suggestion]`.

    {RULE-36}: only suggests an unset flag. {RULE-37}: never sets one --
    this function reads `state.a.notes` / `state.b.notes` and returns new
    `Suggestion` objects; it never mutates `state`. {RULE-38}: `evidence`
    is the actual matched span from the notes (original casing, original
    text), not the lower-cased pattern fragment. {RULE-39}: iterating the
    fixed `_SCAN_TABLE` tuple over the fixed `_SIDES` tuple, and returning
    the first match per entry via `re.search`, makes the output a
    deterministic function of `state` alone -- recomputing on unchanged
    notes always yields the same suggestions in the same order, so a
    caller re-rendering does not lose an in-flight acceptance keyed by
    position or identity.
    """
    mode = state.context.mode
    sides: tuple[tuple[Side, SideObservation], ...] = (("A", state.a), ("B", state.b))

    suggestions: list[Suggestion] = []
    for side, side_obs in sides:
        for entry in _SCAN_TABLE:
            if not _mode_allows(entry, mode):
                continue
            if _flag_already_set(entry, side_obs):
                continue
            match = entry.pattern.search(side_obs.notes)
            if match is None:
                continue
            suggestions.append(
                Suggestion(
                    side=side,
                    target=entry.key,
                    kind=entry.kind,  # type: ignore[arg-type]
                    evidence=match.group(0),
                )
            )
    return suggestions
