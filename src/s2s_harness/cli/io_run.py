"""Run persistence and the `s2s audit FILE` input formats.

`docs/CLI_SPEC.md` §Output: "`--json` output is the `EvaluationState` dump
and is the same payload the bridge returns, so both interfaces are
testable with one fixture set." `to_json_dict` below is the one place that
envelope is built, so the bridge (future wave, `src/s2s_harness/bridge/`)
has exactly one function to reuse rather than a second implementation to
drift from.

The envelope nests `state` (the real `EvaluationState.model_dump()`)
alongside `track_b` / `agreement` / `submission`, which are CLI-local types
(`dual_track.py`) because no teammate owns `models/state.py` this wave --
see that module's docstring for the full gap note. `state` alone IS
byte-identical to a bare `EvaluationState` dump; the nesting is additive.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]  # no stub package in the dev group yet
from pydantic import ValidationError

from s2s_harness.cli.dual_track import Submission
from s2s_harness.cli.errors import InvalidInputError
from s2s_harness.cli.runner import RunResult
from s2s_harness.models.state import EvaluationState

_FRONTMATTER_DELIM = "---"


def to_json_dict(run: RunResult, submission: Submission | None) -> dict[str, Any]:
    return {
        "state": run.state.model_dump(mode="json"),
        "track_b": run.track_b.to_dict() if run.track_b is not None else None,
        "agreement": run.agreement.to_dict(),
        "submission": submission.to_dict() if submission is not None else None,
        "used_compiled_graph": run.used_compiled_graph,
    }


def write_run(out_dir: Path, run: RunResult, submission: Submission | None) -> tuple[Path, Path]:
    """Writes `run.json` + `justification.md` to `out_dir`, `{CLI-12}`."""
    out_dir.mkdir(parents=True, exist_ok=True)
    run_path = out_dir / "run.json"
    justification_path = out_dir / "justification.md"
    run_path.write_text(
        json.dumps(to_json_dict(run, submission), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    text = run.state.polished or run.state.draft
    justification_path.write_text(text + "\n", encoding="utf-8")
    return run_path, justification_path


def parse_audit_file(path: Path) -> tuple[EvaluationState, str]:
    """`s2s audit FILE`, `{CLI-3}`.

    Accepts two shapes:

    - `.json`: either a bare `EvaluationState` dump, or this module's
      envelope (`{"state": {...}, ...}`) -- unwrapped automatically.
    - `.md`: YAML frontmatter between two `---` lines holding the same
      `EvaluationState`-shaped mapping (`context`, `a`, `b`, `picks`),
      followed by the justification prose the rater already submitted.
      This is the "paste what you already submitted" format the spec
      describes; the frontmatter is what lets `normalize -> decide ->
      audit` re-run without regenerating the draft, per CLI_SPEC's
      "check my homework" framing.

    Returns `(state, submitted_justification)`. `state` is validated with
    `context={"allow_derived_fields": True}` -- this is the "already
    normalized reconstruction" case `models/state.py` documents, not raw
    rater input, since a saved run or a hand-written re-audit payload may
    already carry `threshold_all` / `audio_penalized`.
    """
    if not path.exists():
        raise InvalidInputError(f"{path}: no such file")
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InvalidInputError(f"{path}: could not read ({exc})") from exc

    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise InvalidInputError(f"{path}: invalid JSON ({exc})") from exc
        state_payload = payload.get("state", payload) if isinstance(payload, dict) else payload
        justification = ""
        if isinstance(payload, dict):
            justification = payload.get("state", payload).get("polished") or payload.get(
                "state", payload
            ).get("draft", "")
        return _validate_state(state_payload, path), justification

    frontmatter, body = _split_frontmatter(raw, path)
    return _validate_state(frontmatter, path), body.strip()


def _split_frontmatter(raw: str, path: Path) -> tuple[dict[str, Any], str]:
    lines = raw.splitlines()
    if not lines or lines[0].strip() != _FRONTMATTER_DELIM:
        raise InvalidInputError(
            f"{path}: expected YAML frontmatter delimited by '---' lines "
            "(context/a/b/picks), then the justification prose"
        )
    try:
        end = lines[1:].index(_FRONTMATTER_DELIM) + 1
    except ValueError as exc:
        raise InvalidInputError(
            f"{path}: unterminated frontmatter (missing closing '---')"
        ) from exc
    frontmatter_text = "\n".join(lines[1:end])
    body = "\n".join(lines[end + 1 :])
    try:
        parsed = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError as exc:
        raise InvalidInputError(f"{path}: invalid frontmatter YAML ({exc})") from exc
    if not isinstance(parsed, dict):
        raise InvalidInputError(f"{path}: frontmatter must be a mapping (context/a/b/picks)")
    return parsed, body


def _validate_state(payload: Any, path: Path) -> EvaluationState:
    if not isinstance(payload, dict):
        raise InvalidInputError(f"{path}: state payload must be a mapping")
    try:
        return EvaluationState.model_validate(payload, context={"allow_derived_fields": True})
    except ValidationError as exc:
        raise InvalidInputError(f"{path}: {exc}") from exc
