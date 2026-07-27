"""`transcribe` {GRAPH-2}.

Reads: `audio_inputs`. Writes: `transcripts`, appends to `a.notes` /
`b.notes`. Not LLM (Track A tooling calling an external STT API, per
CLAUDE.md design rule 6 -- the rater's own dictated notes only, never the
model clips).

Only reached via the `has_audio` conditional edge (`graph.py`), i.e. only
when `state.audio_inputs` is non-empty. `src/s2s_harness/stt/` does not
exist yet this wave (no teammate owns it in `team_plan.md`'s ownership
table -- see `team_findings.md` [T3]), so this raises a clearly-named
error rather than failing silently or guessing at an adapter shape. No
golden fixture sets `audio_inputs`, so Track A's tested path never
reaches this branch; this is a documented gap for whoever picks up
`STT-*` next, not a defect in the Track A / dual-track guarantee this
wave is responsible for.
"""

from __future__ import annotations

from typing import Any

from s2s_harness.models.state import EvaluationState


def transcribe(state: EvaluationState) -> dict[str, Any]:
    if not state.audio_inputs:
        return {}

    try:
        from s2s_harness.stt import get_provider  # type: ignore[import-untyped]  # STT-*, not built
    except ImportError as exc:
        raise RuntimeError(
            "state.audio_inputs is non-empty but src/s2s_harness/stt/ is not "
            "implemented yet this wave; dictated notes are unsupported until "
            "the STT-* adapters land (see team_findings.md [T3])"
        ) from exc

    provider = get_provider()
    transcripts = dict(state.transcripts)
    a_notes = state.a.notes
    b_notes = state.b.notes

    for side_key, path in state.audio_inputs.items():
        transcript = provider.transcribe(path)
        transcripts[side_key] = transcript
        if side_key == "a":
            a_notes = f"{a_notes}\n{transcript.text}".strip()
        elif side_key == "b":
            b_notes = f"{b_notes}\n{transcript.text}".strip()

    return {
        "transcripts": transcripts,
        "a": state.a.model_copy(update={"notes": a_notes}),
        "b": state.b.model_copy(update={"notes": b_notes}),
    }
