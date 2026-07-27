"""Shared golden-fixture loading and execution helpers.

Owned by T7-fixtures-adversarial (the shared fixture-loading runner, per
the team lead's wave-2 dispatch message -- T6-fixtures-required owns the
six required fixtures and `COVERAGE.md`, T7 owns this module plus the
seven adversarial fixtures, `test_golden.py`, `tests/test_determinism.py`
and `tests/test_token_boundary.py`), per `.claude/team-runs/
2026-07-27-phase3-engine/team_plan.md` Phase B / `docs/EVAL_SPEC.md`.

Used by both `tests/golden/test_golden.py` and `tests/test_determinism.py`
so the two run the exact same pipeline against the exact same fixtures --
determinism has to be checked against the real assembly path, not a second,
possibly-divergent one.

This module wires fixtures to whatever `s2s_harness.rules` currently does.
It must never be the source of an *expected* value: every `expect:` block
in `tests/golden/*.yaml` is authored from `criteria/worked-examples.md` and
`docs/RULES_SPEC.md`/`docs/EVAL_SPEC.md` only, per the anti-drift rule in
`team_plan.md` -- this file is test plumbing, not a fixture author.

Not filename-prefixed with `test_` so pytest does not try to collect it as
a test module in its own right.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from s2s_harness.models.state import (
    EvaluationState,
    Finding,
    Picks,
    SideObservation,
    TaskContext,
    Verdict,
)
from s2s_harness.rules.audit import audit
from s2s_harness.rules.decide import decide
from s2s_harness.rules.draft import build_draft
from s2s_harness.rules.normalize import normalize

GOLDEN_DIR = Path(__file__).parent


def fixture_paths() -> list[Path]:
    """All golden fixtures, sorted for a deterministic collection order."""
    return sorted(GOLDEN_DIR.glob("*.yaml"))


def load_fixture(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: fixture did not parse to a mapping")
    return data


def build_initial_state(data: dict[str, Any]) -> EvaluationState:
    """`EvaluationState` per docs/EVAL_SPEC.md's fixture schema.

    Top-level `mode` is merged into `context` (TaskContext.mode is
    required; the fixture schema keeps it as a sibling key, not nested,
    per the EVAL_SPEC worked-YAML example).
    """
    context_data = dict(data.get("context") or {})
    context_data["mode"] = data["mode"]
    context = TaskContext(**context_data)
    a = SideObservation(side="A", **(data.get("a") or {}))
    b = SideObservation(side="B", **(data.get("b") or {}))
    picks = Picks(**(data.get("picks") or {}))
    return EvaluationState(context=context, a=a, b=b, picks=picks)


def run_pipeline(state: EvaluationState) -> tuple[Verdict, list[Finding], str]:
    """normalize -> decide -> audit -> build_draft, per GRAPH_SPEC section 2's
    node order (`normalize`, `decide`, `audit`, `draft`), calling the pure
    rules functions directly rather than the LangGraph node wrappers (which
    do not exist yet -- Phase 4).
    """
    a_norm = normalize(state.a, state.context)
    b_norm = normalize(state.b, state.context)
    verdict = decide(a_norm, b_norm, state.picks)
    mid_state = state.model_copy(update={"a": a_norm, "b": b_norm, "verdict": verdict})
    findings = audit(mid_state, verdict)
    final_state = mid_state.model_copy(update={"findings": findings})
    draft_text = build_draft(final_state, verdict)
    return verdict, findings, draft_text


def run_fixture(path: Path) -> tuple[dict[str, Any], Verdict, list[Finding], str]:
    data = load_fixture(path)
    state = build_initial_state(data)
    verdict, findings, draft_text = run_pipeline(state)
    return data, verdict, findings, draft_text
