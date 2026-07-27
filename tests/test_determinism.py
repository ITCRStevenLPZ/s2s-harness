"""{EVAL-15}: run every `tests/golden/*.yaml` fixture 50 times and assert a
byte-identical verdict, trace, finding set and draft on every run.

This is the executable form of CLAUDE.md's determinism rule ("Never
iterate a set or an unordered dict where output order matters") and of
`docs/RULES_SPEC.md` {RULE-41} (`decide` is a pure function of
`(a.threshold_all, b.threshold_all, picks)`) and {RULE-42}
(`build_draft` is non-empty whenever `verdict.overall` is set, and by
extension must be the *same* non-empty string every time).

Reuses `tests/golden/_golden_lib.py` -- the same fixture-loading and
pipeline-running code `tests/golden/test_golden.py` uses -- so this checks
determinism of the real assembly path, not a second, possibly-divergent
one. Fixture discovery is generic (`_golden_lib.fixture_paths`); a new
`tests/golden/*.yaml` is covered automatically, no edit needed here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.golden._golden_lib import fixture_paths, run_fixture

FIXTURE_PATHS = fixture_paths()

# 50 runs total per {EVAL-15}'s literal wording ("run every fixture 50
# times"), not 50 *extra* runs on top of an implicit first one.
_RUN_COUNT = 50


def _snapshot(verdict: Any, findings: list[Any], draft_text: str) -> tuple[Any, Any, str]:
    """A single comparable, hashable-by-equality value for one pipeline run.

    `Verdict`/`Finding` are Pydantic models; `.model_dump()` gives a plain
    dict tree that compares by value (including list order, which is
    exactly what we want to catch -- an accidental set/dict reordering
    would show up as a list-order mismatch here).
    """
    return (
        verdict.model_dump(),
        [finding.model_dump() for finding in findings],
        draft_text,
    )


@pytest.mark.parametrize("path", FIXTURE_PATHS, ids=[p.stem for p in FIXTURE_PATHS])
def test_fixture_is_deterministic_across_fifty_runs(path: Path) -> None:
    snapshots = []
    for _ in range(_RUN_COUNT):
        _data, verdict, findings, draft_text = run_fixture(path)
        snapshots.append(_snapshot(verdict, findings, draft_text))

    baseline = snapshots[0]
    for index, snapshot in enumerate(snapshots[1:], start=1):
        assert snapshot == baseline, (
            f"{path.stem}: run {index + 1} of {_RUN_COUNT} diverged from run 1 -- "
            "a pure engine must never do this; look for set iteration or "
            "unordered dict traversal on an output path"
        )
