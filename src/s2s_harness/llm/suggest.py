"""LLM role: `suggest` -- notes + catalogue -> `Suggestion[]`, same shape
`rules.scanner.scan` emits.

Dual-track architecture (CLAUDE.md design rule 2, amended Wave 3b): one
of the four sanctioned Track B call sites. `rules.scanner.scan`'s
bilingual regex table stays -- it is free, instant and deterministic
(`team_plan.md`: "The LLM adds recall on top; it does not replace it").
This module produces additional candidate `Suggestion` objects the
regex table missed (paraphrase, indirection, code-switching mid-sentence)
so the two lists merge and dedupe downstream (merge point is a node
concern, outside this file's ownership -- see `docs/GRAPH_SPEC.md`
`{GRAPH-3}`, owned by T3).

Reuses `models.state.Suggestion` directly (not a parallel type), per
`team_plan.md`: "`suggest` must emit the same `Suggestion` shape as
`scan`". Mirrors `rules/scanner.py`'s contract point for point:

- {RULE-36}: a suggestion is produced only when the corresponding flag is
  currently unset -- enforced here by passing each side's already-set
  flags into the prompt and rejecting (whole-response) any suggestion
  that names an already-set flag.
- {RULE-37}: `suggest` never sets a flag, only proposes one; this module
  returns `Suggestion` objects, never mutates `EvaluationState`.
- {RULE-38}: `evidence` must be the actual matched span from the notes,
  not a paraphrase -- enforced here by rejecting (whole-response) any
  suggestion whose `evidence` is not a verbatim substring of the
  relevant side's notes.
- {RULE-39} / {GRAPH-15}: catalogue keys are mode-scoped; validated
  against `rules.catalog.profile_for(mode)` the same way
  `rules/scanner.py`'s `_mode_allows` does.

Cites: {CRIT-4}/{CRIT-5}/{CRIT-6} (the three catalogues), {RULE-1}
-{RULE-4} (keys and display strings).

Wired against `s2s_harness.llm.client.complete()`, the async facade T1
built for the four LLM roles -- not the lower-level `LLMClient`. No
`client`/`model` parameter; `complete()` resolves the process-wide
provider and model from environment. `LlmDegraded.reason` uses T1's
canonical `LLMSkipReason` vocabulary and is propagated verbatim
(`except LlmDegraded as exc: ... exc.reason`), never remapped to a
generic local reason. `schema` is forwarded to `complete()` (best-effort,
provider-dialect-dependent) and ALSO embedded as literal JSON text in the
prompt as the reliable cross-provider path; every response is still
parsed/validated client-side regardless -- see `interpret.py`'s module
docstring for the full rationale, replicated identically here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

from s2s_harness.llm.client import LlmDegraded, complete
from s2s_harness.models.state import EvaluationState, Mode, SideObservation, Suggestion
from s2s_harness.rules import catalog

PROMPT_VERSION = "1.0.0"

# T1's canonical `LLMSkipReason` (`llm/client.py`) is used verbatim for
# every failure reason except this one, which this module sets itself
# (state.llm_enabled is False, checked before ever calling `complete()`)
# -- see interpret.py's docstring for the full rationale, replicated
# identically here.
REASON_DISABLED = "disabled"


class _SuggestionList(BaseModel):
    """Wraps `list[Suggestion]` in an object, not a bare array, because a
    JSON Schema response must have an object root for every provider this
    project targets (OpenRouter's OpenAI-compatible schema mode and
    Gemini's structured-output mode both require this -- flagged to T1 to
    confirm against current docs, see team_findings.md).
    """

    model_config = ConfigDict(extra="forbid")

    suggestions: list[Suggestion] = []


@dataclass(frozen=True)
class SuggestOutcome:
    """`value` is `None` exactly when `skipped_reason` is non-empty. An
    empty list is a *successful* outcome (the model found nothing beyond
    what `scan` already flagged), distinct from a degraded `None`.
    """

    value: list[Suggestion] | None
    skipped_reason: str = ""


class _MalformedSuggestOutput(Exception):
    """Internal only. Any single invalid suggestion invalidates the whole
    response (`team_plan.md` "Structured output": "never a partial
    parse") -- this module does not cherry-pick the valid entries out of
    a partially-bad list.
    """


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def _kind_for(mode: Mode) -> dict[str, str]:
    profile = catalog.profile_for(mode)
    mapping: dict[str, str] = {}
    mapping.update({key: "error_cluster" for key in profile.error_clusters})
    mapping.update({key: "threshold_utility" for key in catalog.THRESHOLD_UTILITY_INPUT_KEYS})
    mapping.update({key: "threshold_audio" for key in catalog.THRESHOLD_AUDIO_INPUT_KEYS})
    return mapping


def _already_flagged(side_obs: SideObservation) -> set[str]:
    return (
        set(side_obs.error_clusters)
        | set(side_obs.threshold_utility)
        | set(side_obs.threshold_audio)
    )


def _catalogue_glossary(mode: Mode) -> str:
    profile = catalog.profile_for(mode)
    lines = [
        f"  {key} (error_cluster): {catalog.ERROR_CLUSTERS[key].display(mode)}"
        for key in profile.error_clusters
    ]
    lines += [
        f"  {key} (threshold_utility): {catalog.THRESHOLD_UTILITY[key].display}"
        for key in catalog.THRESHOLD_UTILITY_INPUT_KEYS
    ]
    lines += [
        f"  {key} (threshold_audio): {catalog.THRESHOLD_AUDIO[key].display}"
        for key in catalog.THRESHOLD_AUDIO_INPUT_KEYS
    ]
    return "\n".join(lines)


def _build_system_prompt(mode: Mode) -> str:
    schema = _json_schema_for_mode(mode)
    return (
        "You are a second-pass signal detector for the Live S2S Arena / "
        "Stereo Headphone Check project, running alongside a bilingual "
        "regex scanner. Read each side's notes (Spanish, English, or "
        "mixed) and propose catalogue flags the notes support, INCLUDING "
        "ones a keyword scanner would miss -- paraphrase, indirection, "
        "code-switching mid-sentence, sarcasm. Never propose a flag the "
        "notes do not support, and never propose a flag already listed "
        "as already-set for that side (given to you below).\n\n"
        "Catalogue (key: meaning), scoped to this task's mode:\n"
        f"{_catalogue_glossary(mode)}\n\n"
        "For each proposal, return: side (A or B), target (one catalogue "
        "key above), kind (error_cluster / threshold_utility / "
        "threshold_audio -- must match the key's category above), and "
        "evidence: the EXACT substring copied verbatim from that side's "
        "notes that supports the flag. evidence must be a real, "
        "character-for-character quote from the notes, not a summary or "
        "paraphrase -- copy it exactly, including original casing and "
        "punctuation.\n\n"
        "If nothing new is supported, return an empty list. Respond with "
        "a single JSON object matching EXACTLY this shape (no markdown "
        "code fences, no commentary before or after it):\n"
        f"{json.dumps(schema)}"
    )


def _build_user_prompt(state: EvaluationState) -> str:
    mode = state.context.mode
    a_flagged = _already_flagged(state.a)
    b_flagged = _already_flagged(state.b)
    return (
        f"Mode: {mode}\n\n"
        f"SIDE A notes:\n{state.a.notes or '(no notes provided)'}\n"
        f"SIDE A already-flagged (do not repeat these): "
        f"{sorted(a_flagged) if a_flagged else 'none'}\n\n"
        f"SIDE B notes:\n{state.b.notes or '(no notes provided)'}\n"
        f"SIDE B already-flagged (do not repeat these): "
        f"{sorted(b_flagged) if b_flagged else 'none'}"
    )


# ---------------------------------------------------------------------------
# Schema and validation
# ---------------------------------------------------------------------------


def _json_schema_for_mode(mode: Mode) -> dict[str, Any]:
    """Hand-built, not `_SuggestionList.model_json_schema()`, for the same
    reason as `interpret._json_schema_for_mode`: `target`'s valid values
    are mode-scoped for `error_cluster` kind and this needs to be
    generated per call.
    """
    profile = catalog.profile_for(mode)
    all_targets = (
        list(profile.error_clusters)
        + list(catalog.THRESHOLD_UTILITY_INPUT_KEYS)
        + list(catalog.THRESHOLD_AUDIO_INPUT_KEYS)
    )
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["suggestions"],
        "properties": {
            "suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["side", "target", "kind", "evidence"],
                    "properties": {
                        "side": {"type": "string", "enum": ["A", "B"]},
                        "target": {"type": "string", "enum": all_targets},
                        "kind": {
                            "type": "string",
                            "enum": ["error_cluster", "threshold_utility", "threshold_audio"],
                        },
                        "evidence": {"type": "string"},
                    },
                },
            }
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
        raise _MalformedSuggestOutput(f"response is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise _MalformedSuggestOutput("parsed JSON is not an object")
    return parsed


def _validate(payload: dict[str, Any]) -> list[Suggestion]:
    try:
        wrapped = _SuggestionList.model_validate(payload)
    except ValidationError as exc:
        raise _MalformedSuggestOutput(str(exc)) from exc
    return wrapped.suggestions


def _validate_against_state(suggestions: list[Suggestion], state: EvaluationState) -> None:
    """Everything `_json_schema_for_mode`'s enums cannot express because it
    depends on the *current state*, not just the mode: kind/target
    category agreement, evidence-is-a-verbatim-substring ({RULE-38}), and
    not repeating an already-set flag ({RULE-36}).
    """
    mode = state.context.mode
    kind_for_key = _kind_for(mode)
    notes_by_side = {"A": state.a.notes, "B": state.b.notes}
    flagged_by_side = {"A": _already_flagged(state.a), "B": _already_flagged(state.b)}

    for s in suggestions:
        expected_kind = kind_for_key.get(s.target)
        if expected_kind is None or expected_kind != s.kind:
            raise _MalformedSuggestOutput(
                f"target {s.target!r} does not belong to kind {s.kind!r} for mode {mode}"
            )
        if s.target in flagged_by_side[s.side]:
            raise _MalformedSuggestOutput(
                f"side {s.side}: target {s.target!r} is already flagged ({{RULE-36}})"
            )
        if s.evidence not in notes_by_side[s.side]:
            raise _MalformedSuggestOutput(
                f"side {s.side}: evidence is not a verbatim substring of the notes ({{RULE-38}})"
            )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def suggest(state: EvaluationState) -> SuggestOutcome:
    """`suggest` role. Returns candidate `Suggestion` objects for the
    caller (a node, outside this file's ownership) to merge with
    `rules.scanner.scan(state)`'s output and dedupe before presenting to
    the rater. Degrades to `SuggestOutcome(value=None, ...)` on
    `llm_enabled=False`, provider failure, or any malformed/inconsistent
    suggestion in the batch -- never a partial parse.
    """
    if not state.llm_enabled:
        return SuggestOutcome(value=None, skipped_reason=REASON_DISABLED)

    mode = state.context.mode
    system = _build_system_prompt(mode)
    user = _build_user_prompt(state)
    schema = _json_schema_for_mode(mode)

    try:
        response = await complete(
            role="suggest",
            system=system,
            user=user,
            prompt_version=PROMPT_VERSION,
            schema=schema,
        )
    except LlmDegraded as exc:
        return SuggestOutcome(value=None, skipped_reason=exc.reason)

    try:
        payload = _extract_payload(response.text, response.data)
        suggestions = _validate(payload)
        _validate_against_state(suggestions, state)
    except _MalformedSuggestOutput:
        return SuggestOutcome(value=None, skipped_reason="malformed_response")

    return SuggestOutcome(value=suggestions)


# Exported for callers that want to type-check a raw provider payload
# directly (e.g. a fixture or the bridge's own request validation)
# without going through `suggest()`'s network call.
SuggestionListAdapter = TypeAdapter(list[Suggestion])
