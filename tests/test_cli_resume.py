"""Regression test for `--resume`'s checkpointer wiring, Wave 3b follow-up.

T3's commit `9fe71af` made `s2s_harness.graph.sqlite_checkpointer` an
`async def` (its `AsyncSqliteSaver` calls `asyncio.get_running_loop()` at
construction time, so it can only be built inside a running event loop --
see that function's own docstring). `src/s2s_harness/cli/runner.py`
previously called it *synchronously*:

    checkpointer = sqlite_checkpointer(checkpoint_dir / "checkpoints.db")

binding a coroutine object that was never awaited. `compile_graph(
checkpointer=<coroutine>)` then failed inside a blanket `except Exception:
return None`, and `run_graph_for_state` silently fell through to the
uncheckpointed direct node pipeline: `--resume` produced a normal,
un-resumed run, with no error and no checkpoint file, plus a "coroutine
... was never awaited" `RuntimeWarning` -- exactly the kind of silent
failure `warnings.simplefilter("always")` below exists to make loud.

This file fails against that code and passes against the fix
(`_invoke_with_new_checkpointer`: checkpointer construction and
`.ainvoke()` share one `asyncio.run` / one event loop; `--resume` failures
raise `EngineUnavailableError` ({CLI-20}) instead of falling back
silently to path (2)). Only this file under `tests/` is touched here --
`tests/test_dual_track.py`, `tests/golden/`, `tests/test_layering.py` and
`tests/test_token_boundary.py` are T5's / other teammates', untouched.

Reuses `tests/golden/_golden_lib.build_initial_state` / `load_fixture`
against the existing `ex1_houseplant.yaml` fixture rather than inventing
new state-construction code, matching `tests/test_dual_track.py`'s own
convention. `llm_enabled=False` throughout: this file is about the
checkpointer, not Track B, and forcing `--no-llm` keeps the graph on its
short, deterministic path so a slow or misconfigured LLM provider can
never make a checkpointing test flaky.
"""

from __future__ import annotations

import sqlite3
import warnings
from pathlib import Path

from s2s_harness.cli import runner
from s2s_harness.cli.errors import EngineUnavailableError
from tests.golden._golden_lib import GOLDEN_DIR, build_initial_state, load_fixture

_FIXTURE_PATH = GOLDEN_DIR / "ex1_houseplant.yaml"


def _fixture_state() -> object:
    data = load_fixture(_FIXTURE_PATH)
    return build_initial_state(data)


def _checkpoint_count(db_path: Path, thread_id: str) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM checkpoints WHERE thread_id = ?", (thread_id,)
        ).fetchone()
    finally:
        conn.close()
    return int(row[0])


def test_resume_attaches_a_real_checkpointer_with_no_unawaited_coroutine(
    tmp_path: Path,
) -> None:
    state = _fixture_state()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = runner.run_graph_for_state(
            state,  # type: ignore[arg-type]
            llm_enabled=False,
            resume_id="resume-test-thread",
            checkpoint_dir=tmp_path,
        )

    unawaited = [w for w in caught if "was never awaited" in str(w.message)]
    assert unawaited == [], (
        "a 'coroutine was never awaited' warning means sqlite_checkpointer() "
        "was called synchronously instead of awaited -- exactly the "
        "regression this test guards against; "
        f"got: {[str(w.message) for w in caught]}"
    )

    assert result.used_compiled_graph is True
    assert result.state.verdict is not None

    db_path = tmp_path / "checkpoints.db"
    assert db_path.exists(), "--resume must create the sqlite checkpoint database on disk"
    assert _checkpoint_count(db_path, "resume-test-thread") > 0, (
        "the thread's checkpoint(s) must actually be persisted, not just a "
        "database file with no rows in it"
    )


def test_resume_continues_the_same_thread_on_a_second_invocation(tmp_path: Path) -> None:
    """Proves a second `--resume` call actually resumes against the same
    persisted thread rather than silently starting fresh every time
    (which is exactly what the bug produced: a normal uncheckpointed run
    on every invocation, indistinguishable from a resume that never
    happened). The checkpoint history for the thread must grow, and the
    (deterministic, Track-A-only) verdict must be identical both times.
    """
    state = _fixture_state()
    thread_id = "resume-test-thread-continued"
    db_path = tmp_path / "checkpoints.db"

    first = runner.run_graph_for_state(
        state,  # type: ignore[arg-type]
        llm_enabled=False,
        resume_id=thread_id,
        checkpoint_dir=tmp_path,
    )
    assert first.used_compiled_graph is True
    first_count = _checkpoint_count(db_path, thread_id)
    assert first_count > 0

    second = runner.run_graph_for_state(
        state,  # type: ignore[arg-type]
        llm_enabled=False,
        resume_id=thread_id,
        checkpoint_dir=tmp_path,
    )
    assert second.used_compiled_graph is True
    second_count = _checkpoint_count(db_path, thread_id)
    assert second_count > first_count, (
        "resuming the same thread a second time must add to its checkpoint "
        "history, not merely leave an unrelated fresh run's file behind"
    )
    assert second.state.verdict == first.state.verdict


def test_resume_failure_raises_rather_than_falling_back_silently(tmp_path: Path) -> None:
    """A `--resume` run that cannot attach a checkpointer must surface a
    loud `EngineUnavailableError` ({CLI-20}), never a silent, uncheckpointed
    run through the direct node pipeline. Forces the failure with a file
    at the checkpoint path that is not a valid sqlite database at all.
    """
    state = _fixture_state()
    bogus_db = tmp_path / "checkpoints.db"
    bogus_db.write_bytes(b"not a sqlite database at all")

    try:
        runner.run_graph_for_state(
            state,  # type: ignore[arg-type]
            llm_enabled=False,
            resume_id="resume-failure-thread",
            checkpoint_dir=tmp_path,
        )
    except EngineUnavailableError:
        return
    raise AssertionError(
        "expected EngineUnavailableError when the checkpointer cannot attach; "
        "silently falling back to an uncheckpointed run is the regression "
        "this test guards against"
    )
