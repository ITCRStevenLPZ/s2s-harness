"""LLM role: `judge` -- full state + criteria -> Track B's own verdict,
reasoning and confidence.

Dual-track architecture (CLAUDE.md design rule 2, amended Wave 3b): one
of the four sanctioned Track B call sites. `judge` is an *independent*
second opinion, not a second implementation of `rules.decide.decide`. It
is shown beside Track A's verdict, never in place of it, and never
resolves a disagreement for the rater (`team_plan.md`: "Disagreement
between tracks is the product, not a bug. Surface it... The rater
submits. Default is Track A's verdict. Overriding with Track B's is
explicit, one keystroke, and recorded. Nothing auto-applies.") -- the
UI/CLI mechanics of that presentation belong to T3/T4, outside this
file's ownership; this module only produces the `JudgeVerdict` value.

`judge` reads notes and structured state, **never audio**. This binds
CLAUDE.md design rule 6, amended Wave 3b: "This now also binds `judge`:
it reads the rater's notes and structured state, never audio."
`docs/STT_SPEC.md` section 6 (out of scope for STT: "Transcribing or
analysing the model clips") is unchanged by this wave and this module
has no audio input path at all -- `EvaluationState.audio_inputs` /
`.transcripts` are never read here.

Driver vocabulary matches `rules/decide.py`'s three hierarchy labels
exactly ({RULE-14}/{RULE-15}, reproduced in `rules/draft.py` as
`_DRIVER_NATURALNESS` / `_DRIVER_UTILITY` / `_DRIVER_AUDIO`), so a caller
can compare Track A's `Verdict.driver` and Track B's `JudgeVerdict.driver`
directly to render disagreement (`team_plan.md`'s stated purpose). Kept
as a local literal, not imported from `rules/draft.py`, per the
self-contained-module convention already used across `rules/` -- and
because `rules/` may not be imported by anything that also imports an
LLM SDK's transitive dependency chain into the same module namespace
without care; keeping the three strings as a plain tuple here avoids
that question entirely.

Cites: {CRIT-1} (North Star), {CRIT-2} (hierarchy), {CRIT-4} (threshold
gate, including the "rater explicitly argues the breach is minor"
override -- `judge` may weigh such an argument if it appears in the
notes, since it reads notes, but does not require it as a precondition
the way `rules/decide.py`'s gate does), {CRIT-5} (audio tolerance),
{CRIT-6} (error clusters, reportable not disqualifying), {CRIT-7}
(scenario inversion), {CRIT-9} (the justification contract's five
elements -- `judge.reasoning` is asked to cover the same five, so its
shape is comparable to Track A's draft even though the two are generated
by different mechanisms).

Wired against `s2s_harness.llm.client.complete()`, the async facade T1
built for the four LLM roles -- not the lower-level `LLMClient`. No
`client`/`model` parameter; `complete()` resolves the process-wide
provider and model from environment. `LlmDegraded.reason` uses T1's
canonical `LLMSkipReason` vocabulary and is propagated verbatim
(`except LlmDegraded as exc: ... exc.reason`). `schema` is forwarded to
`complete()` (best-effort, provider-dialect-dependent) and ALSO embedded
as literal JSON text in the prompt -- see `interpret.py`'s module
docstring for the full rationale, replicated identically here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from s2s_harness.llm.client import LlmDegraded, complete
from s2s_harness.models.state import EvaluationState, Mode, Pick, Side
from s2s_harness.rules import catalog

PROMPT_VERSION = "1.0.0"

# T1's canonical `LLMSkipReason` (`llm/client.py`) is used verbatim for
# every failure reason except this one, which this module sets itself --
# see interpret.py's docstring for the full rationale.
REASON_DISABLED = "disabled"

# {RULE-14}/{RULE-15}, reproduced from rules/draft.py's
# _DRIVER_NATURALNESS/_DRIVER_UTILITY/_DRIVER_AUDIO -- see module
# docstring for why this is a local copy, not an import.
_DRIVER_LABELS = ("Naturalness / Engagement", "Utility", "Audio Quality")


class JudgeVerdict(BaseModel):
    """Track B's own verdict. Deliberately shaped like
    `models.state.Verdict` (STATE-13: `overall`, `driver`, `gated`,
    `gated_side`) with two additions this role contributes that Track A's
    pure function cannot: `confidence` and free-text `reasoning`. Not a
    subclass of `Verdict` and never written to `EvaluationState.verdict`
    -- that field is Track A's alone; the caller stores this separately
    (a `judge_verdict`-shaped field is T3's node/state design, outside
    this file's ownership).
    """

    model_config = ConfigDict(extra="forbid")

    overall: Pick
    driver: str
    confidence: float
    reasoning: str
    gated: bool
    gated_side: Side | None = None

    @field_validator("confidence")
    @classmethod
    def _confidence_in_range(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return value

    @model_validator(mode="after")
    def _driver_matches_overall(self) -> JudgeVerdict:
        if self.overall in ("A", "B") and self.driver not in _DRIVER_LABELS:
            raise ValueError(
                f"driver must be one of {_DRIVER_LABELS} when overall is A/B, "
                f"got {self.driver!r}"
            )
        if not self.driver.strip():
            raise ValueError("driver must not be empty")
        return self

    @model_validator(mode="after")
    def _gated_side_consistent(self) -> JudgeVerdict:
        if self.gated and self.gated_side is None:
            raise ValueError("gated_side must be set when gated is true")
        if not self.gated and self.gated_side is not None:
            raise ValueError("gated_side must be null when gated is false")
        if self.gated_side is not None and self.overall in ("A", "B"):
            if self.gated_side == self.overall:
                raise ValueError(
                    "gated_side must not equal the winning overall side "
                    "({CRIT-4}: a breaching side should not be preferred "
                    "over a clean one)"
                )
        return self


@dataclass(frozen=True)
class JudgeOutcome:
    """`value` is `None` exactly when `skipped_reason` is non-empty."""

    value: JudgeVerdict | None
    skipped_reason: str = ""


class _MalformedJudgeOutput(Exception):
    """Internal only. Unifies every "cannot be trusted" path into one
    degrade branch, per the same all-or-nothing rule the other three
    roles apply.
    """


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def _artifact_noun(mode: Mode) -> str:
    return "conversation" if mode == "conversation" else "clip"


def _catalogue_glossary(mode: Mode) -> str:
    profile = catalog.profile_for(mode)
    lines = [
        f"  {catalog.ERROR_CLUSTERS[key].display(mode)}"
        for key in profile.error_clusters
        if catalog.ERROR_CLUSTERS[key].scored_as is None
    ]
    utility_lines = [f"  {entry.display}" for entry in catalog.THRESHOLD_UTILITY.values()]
    audio_lines = [f"  {entry.display}" for entry in catalog.THRESHOLD_AUDIO.values()]
    return (
        "Reportable error clusters (report, do not disqualify):\n"
        + "\n".join(lines)
        + "\nThreshold breaches, utility side (gate the vote):\n"
        + "\n".join(utility_lines)
        + "\nThreshold breaches, audio side (gate the vote):\n"
        + "\n".join(audio_lines)
    )


def _build_system_prompt(mode: Mode) -> str:
    noun = _artifact_noun(mode)
    return (
        "You are an independent judge for the Live S2S Arena / Stereo "
        "Headphone Check project, forming your OWN opinion from the "
        f"structured record of a {noun} comparison between side A and "
        "side B. You are not asked to reproduce a deterministic "
        "algorithm -- you are a second, independent read of the same "
        "evidence, shown beside a rules-based verdict so the two can be "
        "compared. Disagreement is useful; do not try to match any "
        "verdict you are not shown.\n\n"
        "PROJECT NORTH STAR: a spontaneous, natural, aesthetically "
        f"pleasing {noun}, like talking to a friend, not querying an "
        "assistant (CRIT-1).\n\n"
        "HIERARCHY (CRIT-2): Naturalness/Engagement/Aesthetics > Utility "
        "> Audio Quality. Utility and Audio Quality must each clear a "
        "basic threshold -- no misinformation, no hallucination, no "
        "jarring audio errors. Naturalness only carries its full weight "
        "once both sides clear that bar. A side that breaches the "
        "threshold while the other is clean should not be preferred, "
        "UNLESS the notes explicitly argue, with evidence, that the "
        "breach is minor and naturalness still wins (CRIT-4) -- weigh "
        "such an argument if the notes make it, do not require it.\n\n"
        "AUDIO TOLERANCE (CRIT-5): slight room tone or faint \"air\" is "
        "NOT a penalty. \"Both Good\" on Audio Quality is illegal when "
        "either side has a noticeable artifact.\n\n"
        f"{_catalogue_glossary(mode)}\n\n"
        "SCENARIO INVERSION (CRIT-7): in hallucination-fishing / redteam "
        "/ false-premise scenarios, a side that rejects or corrects the "
        "false claim is SUCCEEDING, not failing. Never score correct "
        "pushback as a refusal.\n\n"
        "You read only the rater's own notes and the structured record "
        "below -- never audio, and there is none available to you.\n\n"
        "Produce: overall (A, B, TIE for Both Good, or BAD for Both "
        "Bad), driver (exactly one of \"Naturalness / Engagement\", "
        "\"Utility\", \"Audio Quality\" when overall is A or B; a short "
        "phrase explaining why neither separated when overall is TIE or "
        "BAD), confidence (0.0 to 1.0, your own calibrated certainty), "
        "reasoning (2-5 sentences, first person plural \"we\" avoided -- "
        "write as a neutral observer, not as the rater -- covering: the "
        "preference, which hierarchy level decided it and why, specific "
        "evidence from both sides, and an explicit threshold statement), "
        "gated (true if a threshold breach decided the outcome), and "
        "gated_side (the side that breached, or null). Use ONLY what the "
        "record states -- never invent a detail, a turn number, a quote "
        "or a behavior absent from the notes. If the evidence is too "
        "thin to decide confidently, still produce your best-effort "
        "overall pick but say so plainly in reasoning and set confidence "
        "low; do not refuse to answer.\n\n"
        "Respond with a single JSON object matching EXACTLY this shape "
        "(no markdown code fences, no commentary before or after it):\n"
        f"{json.dumps(_JUDGE_SCHEMA)}"
    )


def _build_user_prompt(state: EvaluationState) -> str:
    mode = state.context.mode

    def block(label: str, side: str) -> str:
        obs = state.a if side == "A" else state.b
        return (
            f"SIDE {side}\n"
            f"  Notes: {obs.notes or '(none provided)'}\n"
            f"  Strongest moment: {obs.best or '(not specified)'}\n"
            f"  Weakest moment: {obs.worst or '(not specified)'}\n"
            f"  Error clusters flagged: {obs.error_clusters or 'none'}\n"
            f"  Utility-threshold flags: {obs.threshold_utility or 'none'}\n"
            f"  Audio-threshold flags: {obs.threshold_audio or 'none'}\n"
            f"  Background noise: {obs.background_noise}\n"
            f"  Premise handling: {obs.premise_handling}\n"
            + (f"  Turns: {obs.turns}\n" if mode == "conversation" else "")
            + (f"  Task success: {obs.task_success}\n" if mode == "conversation" else "")
        )

    task_line = (
        f"Scenario: {state.context.scenario or '(not provided)'}"
        if mode == "conversation"
        else f"Prompt: {state.context.prompt or '(not provided)'}"
    )
    ground_truth_line = (
        f"Ground truth: {state.context.ground_truth}\n" if state.context.ground_truth else ""
    )
    return (
        f"Mode: {mode}\n"
        f"Scenario type: {state.context.scenario_type}\n"
        f"{task_line}\n"
        f"{ground_truth_line}\n"
        f"{block('A', 'A')}\n{block('B', 'B')}"
    )


# ---------------------------------------------------------------------------
# Schema and validation
# ---------------------------------------------------------------------------

_JUDGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["overall", "driver", "confidence", "reasoning", "gated", "gated_side"],
    "properties": {
        "overall": {"type": "string", "enum": ["A", "B", "TIE", "BAD"]},
        "driver": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "reasoning": {"type": "string"},
        "gated": {"type": "boolean"},
        "gated_side": {"type": ["string", "null"], "enum": ["A", "B", None]},
    },
}


def _extract_payload(raw_text: str, raw_data: dict[str, Any] | None) -> dict[str, Any]:
    """Prefer `CompletionResult.data`; fall back to parsing `text` as JSON.
    No provider populates `data` today -- see `interpret.py`'s
    `_extract_payload` for the full rationale, replicated here.
    """
    if isinstance(raw_data, dict):
        return raw_data
    try:
        parsed = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise _MalformedJudgeOutput(f"response is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise _MalformedJudgeOutput("parsed JSON is not an object")
    return parsed


def _validate(payload: dict[str, Any]) -> JudgeVerdict:
    try:
        return JudgeVerdict.model_validate(payload)
    except ValidationError as exc:
        raise _MalformedJudgeOutput(str(exc)) from exc


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def judge(state: EvaluationState) -> JudgeOutcome:
    """`judge` role. Produces Track B's independent verdict, reasoning and
    confidence from the full structured state -- never audio
    (`docs/STT_SPEC.md` section 6; CLAUDE.md design rule 6, amended).
    Does not read or depend on Track A's `state.verdict` -- it is meant
    to be an independent read, not a rationalization of Track A's answer.
    Degrades to `JudgeOutcome(value=None, ...)` on `llm_enabled=False`,
    provider failure, or a malformed/self-inconsistent verdict.
    """
    if not state.llm_enabled:
        return JudgeOutcome(value=None, skipped_reason=REASON_DISABLED)

    mode = state.context.mode
    system = _build_system_prompt(mode)
    user = _build_user_prompt(state)

    try:
        response = await complete(
            role="judge",
            system=system,
            user=user,
            prompt_version=PROMPT_VERSION,
            schema=_JUDGE_SCHEMA,
        )
    except LlmDegraded as exc:
        return JudgeOutcome(value=None, skipped_reason=exc.reason)

    try:
        payload = _extract_payload(response.text, response.data)
        verdict = _validate(payload)
    except _MalformedJudgeOutput:
        return JudgeOutcome(value=None, skipped_reason="malformed_response")

    return JudgeOutcome(value=verdict)
