"""`transcribe` {GRAPH-2}.

Reads: `audio_inputs`. Writes: `transcripts`, appends to `a.notes` /
`b.notes`. Not LLM (Track A tooling calling an external STT API, per
CLAUDE.md design rule 6 -- the rater's own dictated notes only, never the
model clips).

Only reached via the `has_audio` conditional edge (`graph.py`), i.e. only
when `state.audio_inputs` is non-empty. `src/s2s_harness/stt/` is Phase 6
(`docs/BUILD_PLAN.md`), explicitly deferred this wave -- no teammate owns
it in `team_plan.md`'s ownership table (see `team_findings.md` [T3]).

Deliberately does **not** import a module that does not exist. An
earlier version of this node did (`from s2s_harness.stt import
get_provider`, guarded by `try`/`except ImportError`), which the team
lead correctly flagged: a broken import inside a `try` still needs to be
distinguished from "this deliberately isn't built yet," and a real STT
package landing later with a *different* shape than guessed here would
have silently produced a confusing `ImportError` instead of this
function's own clear message. This version raises `NotImplementedError`
directly, naming the gap, with no import attempt of any kind -- `{GRAPH-2}`
and the `has_audio` conditional edge stay structurally intact (the node
exists, is reachable, and is exercised by nothing today since no golden
fixture sets `audio_inputs`), and there is nothing to break when Phase 6
actually lands: whoever builds `src/s2s_harness/stt/` replaces the body
of this function, not its signature or its place in the graph.
"""

from __future__ import annotations

from typing import Any

from s2s_harness.models.state import EvaluationState


def transcribe(state: EvaluationState) -> dict[str, Any]:
    if not state.audio_inputs:
        return {}

    raise NotImplementedError(
        "state.audio_inputs is non-empty but src/s2s_harness/stt/ (Phase 6, "
        "docs/BUILD_PLAN.md) is not implemented yet; dictated notes are "
        "unsupported until the STT-* adapters land (see team_findings.md [T3])"
    )
