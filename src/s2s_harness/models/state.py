"""Pydantic state schema for the S2S Arena harness.

Transcribed field-for-field from `docs/GRAPH_SPEC.md` section 1 (STATE-*,
pending T1's spec-ID retrofit). Do not add fields or rename keys here without
updating that spec first -- this module is a faithful transcription, not a
redesign.

Layering (`docs/ARCHITECTURE.md`): this package may import Pydantic and
stdlib typing/path plumbing only. It must never import
`s2s_harness.rules` -- that would invert the documented layer boundary
(`models/` is the base layer; `rules/` builds pure logic on top of these
types). Two consequences of that constraint shape this file, both explained
where they occur below:

1. Validating that `error_clusters` / `threshold_utility` / `threshold_audio`
   keys belong to `rules.catalog`'s catalogues cannot be done by importing
   the catalogue here. The check is wired through Pydantic's validation
   `context`, but -- per lead review, see `team_findings.md` [T3] -- it
   must be **fail-closed by default**, not fail-open when no context is
   supplied: the catalogue is a fixed, closed vocabulary known at import
   time, so "we cannot know the keys without context" was not a real
   obstacle, it was a bug. The default key sets are transcribed verbatim
   from RULES_SPEC section 1 as module-level constants (`_ERROR_CLUSTER_KEYS`
   etc. below), the same duplication-with-a-drift-test pattern already
   accepted for `Mode` (this file vs. `rules/catalog.py`). `context` can
   still *override* the set used per field (e.g. `nodes/ingest.py` passing
   `rules.catalog`'s own tuples, or a mode-filtered subset), but absence of
   context means "use the hardcoded default", never "skip the check".
   `tests/test_layering.py` asserts these constants stay identical to
   `rules.catalog`'s exported tuples, so drift fails the build.

   T2 (`rules/catalog.py`, see `team_findings.md` [T2]) also flagged that
   two catalogue keys -- `premise_redteam` (threshold_utility) and
   `notable_noise` (threshold_audio) -- are themselves computed by
   `normalize` (RULES_SPEC section 2) and must never appear in *raw rater
   input* even though the fields that hold them are otherwise
   caller-settable. The default threshold sets below therefore exclude
   them (`_THRESHOLD_UTILITY_INPUT_KEYS` / `_THRESHOLD_AUDIO_INPUT_KEYS`);
   `context={"allow_derived_fields": True}` switches both the derived-field
   guard (below) and this membership check over to the full sets in one
   move, matching "this payload is an already-normalized reconstruction,
   not raw rater input" as a single concept.
2. `SideObservation.threshold_all` / `.audio_penalized` are derived by
   `rules.normalize` and must never be caller-supplied. The public
   constructor rejects their presence; `rules.normalize` (or any trusted
   internal reconstruction, e.g. replaying a saved run) writes them via
   `SideObservation.model_copy(update=...)`, which does not re-run
   validators. See `_reject_derived_on_input` and `with_derived` below.
   `with_derived` also accepts updated `threshold_utility` /
   `threshold_audio` in the same call, because RULES_SPEC section 2 has
   `normalize` append `notable_noise` / `premise_redteam` into those two
   fields before computing `threshold_all`; all four fields are written
   atomically in one `model_copy` so the state is never observed half
   updated.

See `team_findings.md` under `[T3]` for the full rationale and the open
ratification items sent to T1 (`Transcript` definition location) and T2
(catalogue key contract).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

# ---------------------------------------------------------------------------
# Literal aliases -- GRAPH_SPEC section 1, verbatim
# ---------------------------------------------------------------------------

Side = Literal["A", "B"]
Pick = Literal["A", "B", "TIE", "BAD"]  # TIE = "Both Good", BAD = "Both Bad"
Mode = Literal["conversation", "clips"]
Noise = Literal["clean", "slight", "notable"]
Premise = Literal["na", "pushback", "hedged", "accepted"]
Success = Literal["pass", "partial", "fail"]
Severity = Literal["error", "warning", "info", "ok"]

ScenarioType = Literal[
    "standard",
    "redteam",
    "premise",
    "instruction",
    "interrupt",
    "emotional",
    "roleplay",
    "creative",
]

# Fields on SideObservation that only rules.normalize may write. Presence of
# either key in a caller's input is rejected unless the validation context
# explicitly marks the payload as an already-normalized reconstruction.
_DERIVED_FIELDS = frozenset({"threshold_all", "audio_penalized"})

# ---------------------------------------------------------------------------
# Closed catalogue vocabulary -- default (context-free) key sets for
# SideObservation._flag_keys_known, transcribed verbatim from RULES_SPEC.md
# section 1. Duplicated intentionally: models/ may not import
# rules/catalog.py (see module docstring above). This is the SAME
# duplication-with-a-drift-test pattern already accepted for `Mode`
# (compare `rules/catalog.py`'s own `Mode = Literal[...]`); do not
# "simplify" this by importing rules.catalog, that reopens the layering
# question the lead already reviewed and accepted.
#
# tests/test_layering.py asserts these stay identical to rules.catalog's
# exported tuples (`ERROR_CLUSTER_KEYS`, `THRESHOLD_UTILITY_KEYS`,
# `THRESHOLD_UTILITY_INPUT_KEYS`, `THRESHOLD_AUDIO_KEYS`,
# `THRESHOLD_AUDIO_INPUT_KEYS`), so a future edit to one catalogue that
# misses the other fails the build instead of silently diverging.
# ---------------------------------------------------------------------------

_ERROR_CLUSTER_KEYS: frozenset[str] = frozenset(
    {
        "repetitive",
        "degradation",
        "awkward_silence",
        "embodied",
        "speech_recognition",
        "interrupts_user",
        "ignores_interruption",
        "robotic_intonation",
        "over_structured",
    }
)

_THRESHOLD_UTILITY_KEYS: frozenset[str] = frozenset(
    {"hallucination", "false_premise", "instruction_failure", "premise_redteam"}
)
# `premise_redteam` is written only by rules.normalize (RULES_SPEC section 2,
# step 2) -- excluded from the raw-input default, per the docstring above.
_THRESHOLD_UTILITY_INPUT_KEYS: frozenset[str] = _THRESHOLD_UTILITY_KEYS - {"premise_redteam"}

_THRESHOLD_AUDIO_KEYS: frozenset[str] = frozenset(
    {"cutoff", "clicks", "distortion", "dropout", "notable_noise"}
)
# `notable_noise` is written only by rules.normalize (RULES_SPEC section 2,
# step 1) -- excluded from the raw-input default, same reasoning as above.
_THRESHOLD_AUDIO_INPUT_KEYS: frozenset[str] = _THRESHOLD_AUDIO_KEYS - {"notable_noise"}


# ---------------------------------------------------------------------------
# Transcript / Word -- STT_SPEC.md section 2
#
# UNRESOLVED CONFLICT, flagged for T1 (owns STT_SPEC/GRAPH_SPEC) and T5
# (owns ARCHITECTURE.md), not papered over:
#
# T1's ratified resolution (team_findings.md "[T1] Transcript resolution"
# and GRAPH_SPEC STATE-16) keeps a single definition in STT_SPEC section 2 /
# `src/s2s_harness/stt/base.py`, with GRAPH_SPEC only referencing it. That
# is the right call for "one definition, no drift" in isolation, but it
# conflicts with ARCHITECTURE.md's layer table: `stt/` may import `models/`,
# never the reverse, and `EvaluationState.transcripts: dict[str, Transcript]`
# lives in `models/state.py` (this file). Importing `stt.base.Transcript`
# here would invert that boundary exactly the way a `models/` -> `rules/`
# import would, and this package's docstring above says never do that.
#
# Resolution taken for THIS deliverable, pending T1/T5 ratification: define
# `Word`/`Transcript` here (the lower layer, zero extra dependencies, which
# is what STT_SPEC's own field list already is -- text, language, words,
# provider, duration_s, raw), and `stt/base.py` should import them from
# `models.state` instead of redefining them. This preserves T1's "one
# definition" goal while keeping the layer table's arrow direction (stt/ ->
# models/) intact. If T1/T5 rule differently, update this block and
# `stt/base.py` together in the same change -- never let two class bodies
# exist for the same name.
# ---------------------------------------------------------------------------


class Word(BaseModel):
    """One recognized word with optional timing. STT_SPEC section 2."""

    model_config = ConfigDict(extra="forbid")

    text: str
    start_s: float | None = None
    end_s: float | None = None


class Transcript(BaseModel):
    """Provider transcription output. STT_SPEC section 2."""

    model_config = ConfigDict(extra="forbid")

    text: str
    language: str | None = None
    words: list[Word] = []
    provider: str
    duration_s: float | None = None
    raw: dict[str, Any] | None = None  # provider payload, for debugging only


# ---------------------------------------------------------------------------
# Core observation and context models
# ---------------------------------------------------------------------------


class SideObservation(BaseModel):
    side: Side
    notes: str = ""
    best: str = ""  # strongest specific moment
    worst: str = ""  # weakest specific moment
    error_clusters: list[str] = []  # keys from rules.catalog.ERROR_CLUSTERS
    threshold_utility: list[str] = []  # keys from rules.catalog.THRESHOLD_UTILITY
    threshold_audio: list[str] = []  # keys from rules.catalog.THRESHOLD_AUDIO
    background_noise: Noise = "clean"
    premise_handling: Premise = "na"
    turns: int | None = None  # conversation mode only
    task_success: Success | None = None  # conversation mode only

    # derived by `normalize`, never set by the caller -- see module docstring
    threshold_all: list[str] = []
    audio_penalized: bool = False

    model_config = ConfigDict(extra="forbid")

    @field_validator("turns")
    @classmethod
    def _turns_non_negative(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("turns must be non-negative")
        return value

    @model_validator(mode="after")
    def _reject_derived_on_input(self, info: ValidationInfo) -> SideObservation:
        allow_derived = bool(info.context and info.context.get("allow_derived_fields"))
        if not allow_derived and (self.model_fields_set & _DERIVED_FIELDS):
            raise ValueError(
                "threshold_all and audio_penalized are derived by "
                "rules.normalize and must not be supplied as input. Pass "
                "context={'allow_derived_fields': True} to model_validate "
                "only when reconstructing an already-normalized state "
                "(checkpoint resume, saved-run replay)."
            )
        return self

    @model_validator(mode="after")
    def _flag_keys_known(self, info: ValidationInfo) -> SideObservation:
        """Reject unknown catalogue keys. Fail-closed: with no context at
        all, this still enforces the hardcoded default vocabulary below --
        it never silently skips the check. `context` may override the set
        used per field (e.g. a mode-filtered profile); it cannot disable
        the check by being absent. See the module docstring and
        `team_findings.md` [T3] for why the earlier "no context => skip"
        version was a defect, not a feature.
        """
        ctx = info.context or {}
        allow_derived = bool(ctx.get("allow_derived_fields"))
        default_threshold_utility = (
            _THRESHOLD_UTILITY_KEYS if allow_derived else _THRESHOLD_UTILITY_INPUT_KEYS
        )
        default_threshold_audio = (
            _THRESHOLD_AUDIO_KEYS if allow_derived else _THRESHOLD_AUDIO_INPUT_KEYS
        )
        catalogue_fields = {
            "error_clusters": ctx.get("error_cluster_keys", _ERROR_CLUSTER_KEYS),
            "threshold_utility": ctx.get("threshold_utility_keys", default_threshold_utility),
            "threshold_audio": ctx.get("threshold_audio_keys", default_threshold_audio),
        }
        for field_name, valid_keys in catalogue_fields.items():
            supplied = set(getattr(self, field_name))
            unknown = supplied - set(valid_keys)
            if unknown:
                raise ValueError(
                    f"{field_name} contains unknown catalogue key(s): {sorted(unknown)}"
                )
        return self

    def with_derived(
        self,
        *,
        threshold_all: list[str],
        audio_penalized: bool,
        threshold_utility: list[str] | None = None,
        threshold_audio: list[str] | None = None,
    ) -> SideObservation:
        """The only sanctioned way to populate the derived fields.

        For use by `rules.normalize` (and by trusted state reconstruction,
        e.g. replaying a saved run). `model_copy` does not re-run validators,
        so this bypasses `_reject_derived_on_input` without weakening it for
        the public constructor / `model_validate` path.

        `threshold_utility` / `threshold_audio` are optional because most
        callers only need to set `threshold_all` / `audio_penalized`; pass
        them too when `normalize` has appended `premise_redteam` or
        `notable_noise` (RULES_SPEC section 2, steps 1-2), so all four
        fields land in a single atomic `model_copy` call.
        """
        update: dict[str, list[str] | bool] = {
            "threshold_all": threshold_all,
            "audio_penalized": audio_penalized,
        }
        if threshold_utility is not None:
            update["threshold_utility"] = threshold_utility
        if threshold_audio is not None:
            update["threshold_audio"] = threshold_audio
        return self.model_copy(update=update)


class Preflight(BaseModel):
    """Conversation mode only."""

    model_config = ConfigDict(extra="forbid")

    headphones: bool = False
    panning_check: bool = False
    scenario_read: bool = False
    listened_isolated: bool = False
    equivalent_prompts: bool = False
    stayed_in_character: bool = False
    interruption_tested: bool = False


class TaskContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Mode
    scenario: str = ""  # conversation: the assigned scenario/persona
    prompt: str = ""  # clips: the question the clips answer
    scenario_type: ScenarioType = "standard"
    ground_truth: str = ""  # clips: the fact, when the prompt embeds a false premise
    prompts_used: list[str] = []  # conversation: the turn prompts, for equivalence review
    preflight: Preflight = Field(default_factory=Preflight)
    skip_reason: str = ""  # non-empty => technical skip, not a vote


class Picks(BaseModel):
    model_config = ConfigDict(extra="forbid")

    naturalness: Pick | None = None
    utility: Pick | None = None
    audio: Pick | None = None
    overall: Pick | None = None


class Verdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall: Pick | None
    driver: str  # human-readable deciding dimension
    gated: bool = False
    gated_side: Side | None = None  # the side that breached the threshold
    trace: list[str] = []  # ordered explanation of the walk


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: Severity
    code: str  # stable identifier, e.g. "AUDIO_BOTH_GOOD_ILLEGAL"
    label: str  # short chip text, e.g. "AUDIO"
    message: str


class Suggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    side: Side
    target: str  # catalog key the scanner matched
    kind: Literal["error_cluster", "threshold_utility", "threshold_audio", "tone"]
    evidence: str  # the matched span from the notes


class EvaluationState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context: TaskContext
    a: SideObservation
    b: SideObservation
    picks: Picks = Field(default_factory=Picks)
    audio_inputs: dict[str, Path] = {}  # {"a": ..., "b": ...} when dictating
    transcripts: dict[str, Transcript] = {}
    suggestions: list[Suggestion] = []
    verdict: Verdict | None = None
    findings: list[Finding] = []
    draft: str = ""  # deterministic, always populated
    polished: str = ""  # LLM output, may be empty
    llm_enabled: bool = True
    llm_skipped_reason: str = ""
