"""LLM role: `interpret` -- free-form rater notes -> structured proposal.

Dual-track architecture (`.claude/team-runs/2026-07-27-wave3b-dual-track/
team_plan.md`; CLAUDE.md design rule 2, amended Wave 3b): this is one of
the four sanctioned Track B call sites, not the old single-call-site
model. `src/s2s_harness/rules/` and `src/s2s_harness/models/` stay
model-free (CLAUDE.md design rule 1, narrowed) -- this module lives
outside both.

Input: the whole `EvaluationState`, both sides' free-form Spanish/English
notes plus task context. Output: a *proposal* -- each side's strongest
and weakest moment and candidate catalogue flags, restated in structured
form. Never written into `EvaluationState` by this module and never
auto-applied anywhere; the caller (CLI/bridge) presents it for the rater
to accept, edit or discard, the same review step `rules.scanner.scan`'s
suggestions already go through.

Whole-state convention: mirrors `rules.scanner.scan(state)`, which reads
`state.a.notes` / `state.b.notes` but takes the whole state rather than
two note strings (`team_findings.md`, "[lead] Rules-layer public API":
"scan(state) -- takes the WHOLE state, not a.notes/b.notes, despite the
node table's wording"). `interpret(state)` does the same, in one
completion, so the model has `context.scenario`/`context.prompt`,
`scenario_type` and `ground_truth` available when a note is ambiguous
without them.

Cites: {CRIT-1} (North Star framing), {CRIT-4}/{CRIT-5} (threshold
catalogues), {CRIT-6} (error clusters), {CRIT-7} (scenario inversion --
pushback against a false premise is a candidate positive signal, never a
candidate error), {RULE-1}-{RULE-4} (catalogue keys and display strings),
{GRAPH-15} (mode-scoped catalogue profiles -- "do not fork the engine",
implemented here the same way `rules/scanner.py`'s `_mode_allows` does,
via `rules.catalog.profile_for(mode)`), CLAUDE.md design rule 4 amended
("this now binds `interpret`, `suggest` and `judge` too, since all three
can surface text back to the rater") -- `best`/`worst` use the exact
`【...】` placeholder form, via `rules.draft.gap`, when the notes do not
support a value, rather than silently rendering an empty string as if
nothing were missing.

Wired against `s2s_harness.llm.client.complete()` -- the async facade T1
built specifically for the four LLM roles (`client.py`'s
`CompletionResult`/`LlmDegraded` docstrings: "the actual integration
point for interpret/suggest/judge/polish"), not the lower-level
`LLMClient`/`LLMOutcome` pair that facade wraps. `complete()` resolves
the process-wide provider and model from environment on first use
(`S2S_LLM_PROVIDER`, `S2S_LLM_MODEL`) -- this module does not take a
`client` or `model` parameter; there is nothing for a caller to
construct or thread through. `LlmDegraded.reason` uses T1's canonical
`LLMSkipReason` vocabulary (`client.py`'s module docstring: "T2/T3/T4:
use these exact strings, do not invent parallel ones per role") and is
propagated verbatim (`except LlmDegraded as exc: ... exc.reason`) rather
than remapped to a generic local reason -- T1 flagged in
`team_findings.md` that catching this bare and discarding `.reason`
throws away real information (timeout vs. rate-limited vs. malformed).

`schema` IS forwarded to `complete()` (`response_schema` reaches the
configured provider) but is provider-dialect-dependent and best-effort
per T1's docstring -- OpenRouter/OpenAI's JSON-Schema dialect matches
what `_json_schema_for_mode` builds; Gemini's does not (uppercase types,
`nullable` instead of a null union) and may simply be ignored or
rejected there. The schema is therefore ALSO embedded as literal JSON
text in the prompt (`_build_system_prompt`) as the reliable cross
-provider path, and every response is still parsed/validated client-side
(`_extract_payload` / `_validate` / `_check_catalogue_membership`) --
belt-and-suspenders, never a partial parse either way.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from s2s_harness.llm.client import LlmDegraded, complete
from s2s_harness.models.state import EvaluationState, Mode, Noise, Premise, Side
from s2s_harness.rules import catalog
from s2s_harness.rules.draft import frag, gap

PROMPT_VERSION = "1.0.0"

# llm_skipped_reason vocabulary: T1's canonical `LLMSkipReason`
# (`llm/client.py`), reused verbatim rather than remapped. "disabled" is
# set here directly when `state.llm_enabled` is `False` -- a separate,
# earlier gate than `complete()`'s own "disabled" (no provider configured
# at all), per T1's note that a role checks its own `llm_enabled` before
# ever calling `complete()`. Every other failure reason is
# `exc.reason` from a caught `LlmDegraded`, propagated as-is.
# "malformed_response" is also reused for this module's own post-hoc
# validation failures (JSON parse, schema-shape, catalogue-membership)
# since those are the same class of "cannot be trusted" failure T1's
# provider layer already names, and `client.py` asks that no parallel
# string be invented per role.
REASON_DISABLED = "disabled"


class InterpretedSide(BaseModel):
    """One side's proposal.

    Field names deliberately echo `SideObservation` (models/state.py,
    STATE-9) so a caller can map an accepted field 1:1, but this is its
    own type -- never a `SideObservation`, so it can never be mistaken
    for validated state and merged in without the rater's explicit accept
    step. `extra="forbid"` matches the project-wide convention (see
    `team_findings.md` "[lead] Pydantic validation traps") even though
    this model is never itself part of `EvaluationState`.
    """

    model_config = ConfigDict(extra="forbid")

    side: Side
    best: str = ""
    worst: str = ""
    candidate_error_clusters: list[str] = []
    candidate_threshold_utility: list[str] = []
    candidate_threshold_audio: list[str] = []
    candidate_background_noise: Noise | None = None
    candidate_premise_handling: Premise | None = None


class InterpretResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    a: InterpretedSide
    b: InterpretedSide


@dataclass(frozen=True)
class InterpretOutcome:
    """`value` is `None` exactly when `skipped_reason` is non-empty."""

    value: InterpretResult | None
    skipped_reason: str = ""


class _MalformedInterpretOutput(Exception):
    """Internal only. Raised, then caught, to unify every "the model's
    response cannot be trusted" path (schema mismatch, catalogue key
    outside the mode profile, side letter mismatch) into one degrade
    branch. Per `team_plan.md` "Structured output": "If a provider
    returns malformed output, that is a degradation case: fall back to
    Track A and record the reason, never a partial parse" -- so any
    single invalid field discards the *whole* result, it never silently
    drops just that field.
    """


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def _artifact_noun(mode: Mode) -> str:
    return "conversation" if mode == "conversation" else "clip"


def _cluster_glossary(mode: Mode) -> str:
    profile = catalog.profile_for(mode)
    lines = [
        f"  {key}: {catalog.ERROR_CLUSTERS[key].display(mode)}"
        for key in profile.error_clusters
    ]
    return "\n".join(lines)


def _threshold_glossary(keys: tuple[str, ...], table: dict[Any, Any]) -> str:
    return "\n".join(f"  {key}: {table[key].display}" for key in keys)


def _build_system_prompt(mode: Mode) -> str:
    noun = _artifact_noun(mode)
    return (
        "You are assisting a human rater on the Live S2S Arena / Stereo "
        "Headphone Check project. The rater has written free-form notes, "
        f"in Spanish, English, or a mix, about one side of a {noun} "
        "comparison. Restate ONLY what the notes already say, in "
        "structured form. Never add a detail, a moment, a quote or a "
        "judgment the notes do not contain (CRIT-1 through CRIT-9 govern "
        "the project; this task only extracts, it does not decide).\n\n"
        "For EACH side (A and B), extract:\n"
        "- best: the single strongest specific moment the notes describe, "
        "tightened to one clause, in the rater's own words. If the notes "
        "describe no such moment, use the exact placeholder form "
        "【describe the strongest moment here】 -- never leave it "
        "empty and never invent one.\n"
        "- worst: the single weakest specific moment, same rule, "
        "placeholder 【describe the weakest moment here】 when "
        "absent.\n"
        "- candidate_error_clusters: zero or more of these keys, only "
        "when the notes clearly describe the behavior:\n"
        f"{_cluster_glossary(mode)}\n"
        "- candidate_threshold_utility: zero or more of:\n"
        f"{_threshold_glossary(catalog.THRESHOLD_UTILITY_INPUT_KEYS, catalog.THRESHOLD_UTILITY)}\n"
        "- candidate_threshold_audio: zero or more of:\n"
        f"{_threshold_glossary(catalog.THRESHOLD_AUDIO_INPUT_KEYS, catalog.THRESHOLD_AUDIO)}\n"
        "- candidate_background_noise: \"clean\", \"slight\" or "
        "\"notable\" if the notes describe background noise, else null. "
        "A faint room tone or \"air\" is \"slight\", not \"notable\" -- "
        "it is explicitly NOT a penalty on this project (CRIT-5).\n"
        "- candidate_premise_handling: \"na\", \"pushback\", \"hedged\" "
        "or \"accepted\" if the notes describe how the side handled a "
        "false premise or redteam claim, else null. A side that rejects "
        "or corrects a false claim is SUCCEEDING, not failing (CRIT-7) "
        "-- that is \"pushback\", a positive signal, never a candidate "
        "error cluster or threshold flag.\n\n"
        "If a field is not addressed by the notes: candidate lists stay "
        "empty (`[]`), the two enum fields stay `null`. Only best/worst "
        "use the bracket placeholder rule above, because they render as "
        "prose to the rater; the others are structural and an empty/null "
        "value already means \"not stated\", nothing to invent.\n\n"
        f"Valid side letters for this task: {', '.join(('A', 'B'))}. "
        "Respond with a single JSON object matching EXACTLY this shape "
        "(no markdown code fences, no commentary before or after it):\n"
        f"{json.dumps(_json_schema_for_mode(mode))}"
    )


def _build_user_prompt(state: EvaluationState) -> str:
    mode = state.context.mode
    task_line = (
        f"Scenario: {state.context.scenario or '(not provided)'}"
        if mode == "conversation"
        else f"Prompt: {state.context.prompt or '(not provided)'}"
    )
    return (
        f"Mode: {mode}\n"
        f"Scenario type: {state.context.scenario_type}\n"
        f"{task_line}\n\n"
        f"SIDE A notes:\n{state.a.notes or '(no notes provided)'}\n\n"
        f"SIDE B notes:\n{state.b.notes or '(no notes provided)'}"
    )


# ---------------------------------------------------------------------------
# Schema and validation
# ---------------------------------------------------------------------------


def _json_schema_for_mode(mode: Mode) -> dict[str, Any]:
    """Hand-built JSON Schema, not `InterpretResult.model_json_schema()`.

    The candidate-flag enums are mode-scoped ({GRAPH-15}: interruption
    clusters vs. `robotic_intonation`/`over_structured`), and that scoping
    can only be expressed by generating the schema per call from
    `rules.catalog.profile_for(mode)` -- a static Pydantic schema cannot
    vary its enum members by argument. Threshold catalogues are
    mode-agnostic (`rules/catalog.py`: no `Modes` column on either
    threshold table, and `normalize`-derived keys `premise_redteam` /
    `notable_noise` are excluded via `*_INPUT_KEYS`, matching
    `models/state.py`'s own raw-input validation), so those two enums are
    the same in both modes.
    """
    profile = catalog.profile_for(mode)

    def side_schema() -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["side", "best", "worst"],
            "properties": {
                "side": {"type": "string", "enum": ["A", "B"]},
                "best": {"type": "string"},
                "worst": {"type": "string"},
                "candidate_error_clusters": {
                    "type": "array",
                    "items": {"type": "string", "enum": list(profile.error_clusters)},
                },
                "candidate_threshold_utility": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": list(catalog.THRESHOLD_UTILITY_INPUT_KEYS),
                    },
                },
                "candidate_threshold_audio": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": list(catalog.THRESHOLD_AUDIO_INPUT_KEYS),
                    },
                },
                "candidate_background_noise": {
                    "type": ["string", "null"],
                    "enum": ["clean", "slight", "notable", None],
                },
                "candidate_premise_handling": {
                    "type": ["string", "null"],
                    "enum": ["na", "pushback", "hedged", "accepted", None],
                },
            },
        }

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["a", "b"],
        "properties": {"a": side_schema(), "b": side_schema()},
    }


def _extract_payload(raw_text: str, raw_data: dict[str, Any] | None) -> dict[str, Any]:
    """Prefer `CompletionResult.data` when a provider populates it; fall
    back to parsing `text` as JSON otherwise. No provider does today
    (`client.py`'s `CompletionResult` docstring: "always `None`
    currently... parse `text` yourself"), so this always takes the
    `json.loads` branch in practice, but checking `raw_data` first costs
    nothing and means this module does not need to change if that
    changes. Either way, the result is handed to `InterpretResult` for
    full-shape validation next -- this function only gets the bytes into
    a dict, it does not judge correctness.
    """
    if isinstance(raw_data, dict):
        return raw_data
    try:
        parsed = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise _MalformedInterpretOutput(f"response is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise _MalformedInterpretOutput("parsed JSON is not an object")
    return parsed


def _validate(payload: dict[str, Any]) -> InterpretResult:
    """All-or-nothing validation ({team_plan.md} "Structured output":
    never a partial parse). Pydantic's `extra="forbid"` plus the `Literal`
    types on `Noise`/`Premise`/`Side` cover shape and enum-membership for
    those three fields; catalogue-key membership for the three candidate
    lists is enforced separately in `interpret()` after this call,
    because it is mode-scoped and this function has no `mode` argument
    (kept that way so it stays a pure "does this even parse as the
    contract" check, independent of mode).
    """
    try:
        result = InterpretResult.model_validate(payload)
    except ValidationError as exc:
        raise _MalformedInterpretOutput(str(exc)) from exc
    if result.a.side != "A" or result.b.side != "B":
        raise _MalformedInterpretOutput("side letters do not match the a/b slots")
    return result


def _check_catalogue_membership(result: InterpretResult, mode: Mode) -> None:
    profile = catalog.profile_for(mode)
    valid_clusters = set(profile.error_clusters)
    valid_utility = set(catalog.THRESHOLD_UTILITY_INPUT_KEYS)
    valid_audio = set(catalog.THRESHOLD_AUDIO_INPUT_KEYS)
    for side in (result.a, result.b):
        if not set(side.candidate_error_clusters) <= valid_clusters:
            raise _MalformedInterpretOutput(
                f"side {side.side}: candidate_error_clusters outside the {mode} profile"
            )
        if not set(side.candidate_threshold_utility) <= valid_utility:
            raise _MalformedInterpretOutput(
                f"side {side.side}: candidate_threshold_utility contains an unknown key"
            )
        if not set(side.candidate_threshold_audio) <= valid_audio:
            raise _MalformedInterpretOutput(
                f"side {side.side}: candidate_threshold_audio contains an unknown key"
            )


def _apply_placeholder_fallback(result: InterpretResult) -> InterpretResult:
    """Belt-and-suspenders for design rule 4: if the model returned an
    empty `best`/`worst` instead of following the bracket-placeholder
    instruction, replace it here rather than surfacing a blank field as
    if it meant "confirmed nothing". Uses `rules.draft.gap`/`frag`, the
    sanctioned builders (`team_plan.md`'s instruction to T2: "reuse them
    rather than writing the brackets by hand").
    """

    def fix(side: InterpretedSide) -> InterpretedSide:
        best = frag(side.best) or gap("describe the strongest moment here")
        worst = frag(side.worst) or gap("describe the weakest moment here")
        return side.model_copy(update={"best": best, "worst": worst})

    return InterpretResult(a=fix(result.a), b=fix(result.b))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def interpret(state: EvaluationState) -> InterpretOutcome:
    """`interpret` role. Reads `state.a.notes` / `state.b.notes` plus task
    context; proposes structured best/worst and candidate flags. Never
    mutates `state`. Degrades to `InterpretOutcome(value=None,
    skipped_reason=...)` on `llm_enabled=False`, a provider failure, or
    any malformed/out-of-catalogue field -- the caller's job (CLI/bridge,
    outside this file) is to skip presenting a Track B proposal when
    `value is None`, never to partially trust one. No `client`/`model`
    parameter -- `llm.client.complete()` resolves the process-wide
    provider and model from environment itself.
    """
    if not state.llm_enabled:
        return InterpretOutcome(value=None, skipped_reason=REASON_DISABLED)

    mode = state.context.mode
    system = _build_system_prompt(mode)
    user = _build_user_prompt(state)
    schema = _json_schema_for_mode(mode)

    try:
        response = await complete(
            role="interpret",
            system=system,
            user=user,
            prompt_version=PROMPT_VERSION,
            schema=schema,
        )
    except LlmDegraded as exc:
        return InterpretOutcome(value=None, skipped_reason=exc.reason)

    try:
        payload = _extract_payload(response.text, response.data)
        result = _validate(payload)
        _check_catalogue_membership(result, mode)
    except _MalformedInterpretOutput:
        return InterpretOutcome(value=None, skipped_reason="malformed_response")

    return InterpretOutcome(value=_apply_placeholder_fallback(result))
