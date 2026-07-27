"""{EVAL-16}: walk the AST of every file under `src/s2s_harness/rules/` and
`src/s2s_harness/models/` and fail on any banned import (LLM SDK, networking
library, or local I/O library).

This is the pytest form of the invariant CLAUDE.md design rule 1 states
(amended Wave 3b, 2026-07-27 -- narrowed from "the rules engine contains
zero LLM calls" to name `rules/` and `models/` explicitly) and
`scripts/token_boundary_check.py` already implements as the fast,
dependency-free pre-commit hook. Per that script's own module docstring,
this file is the "authoritative pytest version" it mirrors; both call the
exact same `check_file` -- one AST-walk implementation, not two divergent
ones that could drift apart.

WAVE 3B REWORK. This file used to enforce the single-call-site invariant
("only `nodes/polish.py` may import an LLM SDK") and SKIPPED entirely,
because `nodes/polish.py` did not exist yet -- a vacuous pass, not a real
one. That invariant is deprecated in place (CLAUDE.md design rule 2). This
file now enforces the invariant that survives (design rule 1): `rules/` and
`models/` must stay free of LLM SDKs, network calls, and I/O. Both
directories have existed since Phase 3 (`339cc94`), so this suite ENFORCES
rather than skips.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.token_boundary_check import PURE_DIRS, check_file

REPO_ROOT = Path(__file__).resolve().parents[1]
_PURE_DIRS_ABS = tuple(REPO_ROOT / pure_dir for pure_dir in PURE_DIRS)


def _discover_pure_files() -> list[Path]:
    files: list[Path] = []
    for pure_dir in _PURE_DIRS_ABS:
        if pure_dir.exists():
            files.extend(sorted(pure_dir.rglob("*.py")))
    return files


PURE_FILES = _discover_pure_files()


def test_pure_dirs_exist_to_check() -> None:
    """Both `rules/` and `models/` must exist for this suite to enforce
    anything. Their absence would silently turn every test below into a
    vacuous pass over an empty parametrize list -- exactly the failure mode
    this file used to have with `nodes/polish.py` before Wave 3b.
    """
    missing = [d for d in _PURE_DIRS_ABS if not d.exists()]
    assert not missing, (
        f"{missing} do not exist -- the token-boundary check has nothing to "
        "walk for one or both pure directories; this is itself a failure, "
        "not a vacuous pass"
    )


def test_pure_dirs_have_python_files() -> None:
    assert PURE_FILES, (
        f"{_PURE_DIRS_ABS} have no .py files between them -- the "
        "token-boundary check has nothing to walk; this is itself a "
        "failure, not a vacuous pass"
    )


@pytest.mark.parametrize(
    "path",
    PURE_FILES,
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_file_imports_no_banned_module(path: Path) -> None:
    errors = check_file(path)
    assert not errors, "\n".join(errors)


def test_llm_package_is_not_scoped_by_this_check() -> None:
    """Sanity check on the boundary itself, not on any one file's imports.

    `src/s2s_harness/llm/` imports an LLM SDK by design -- that is the
    entire point of Wave 3b's four LLM roles. It must NOT be covered by
    `PURE_DIRS`, or design rule 1 (rules/models stay model-free) and design
    rule 2 (LLM code lives in `llm/`) would directly contradict each other.
    If `llm/` (or any of its parents) is ever added to `PURE_DIRS` by
    mistake, this test fails loudly instead of the contradiction going
    unnoticed until `llm/`'s own tests mysteriously start failing the
    boundary check.
    """
    llm_dir = REPO_ROOT / "src/s2s_harness/llm"
    for pure_dir in _PURE_DIRS_ABS:
        assert pure_dir != llm_dir
        assert pure_dir not in llm_dir.parents
        assert llm_dir not in pure_dir.parents
