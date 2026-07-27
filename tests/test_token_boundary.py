"""{EVAL-16}: walk the AST of everything under `src/s2s_harness/` except
`nodes/polish.py` and fail on any LLM SDK import.

This is the pytest form of the invariant CLAUDE.md design rule 2 states and
`scripts/token_boundary_check.py` already implements as the fast,
dependency-free pre-commit hook. Per that script's own module docstring,
this file is the "authoritative pytest version" it mirrors; both call the
exact same `check_file` -- one AST-walk implementation, not two divergent
ones that could drift apart.

`src/s2s_harness/nodes/polish.py` does not exist yet (Phase 4, GRAPH-*).
Its absence is not an error here: every file under `src/s2s_harness/` is
checked and none is exempted until the sanctioned file exists to carry the
exemption, exactly as `token_boundary_check.py` documents.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.token_boundary_check import SANCTIONED_RELATIVE_PATH, SRC_ROOT, check_file

REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT_ABS = REPO_ROOT / SRC_ROOT


def _is_sanctioned(path: Path) -> bool:
    """Same check as `token_boundary_check._is_sanctioned`, made independent
    of the process's current working directory (this test may run from any
    invocation directory pytest is given), by resolving against
    `REPO_ROOT` explicitly rather than `Path.cwd()`.
    """
    try:
        relative = path.resolve().relative_to(REPO_ROOT)
    except ValueError:
        return False
    return relative == SANCTIONED_RELATIVE_PATH


def _discover_source_files() -> list[Path]:
    if not _SRC_ROOT_ABS.exists():
        return []
    return sorted(_SRC_ROOT_ABS.rglob("*.py"))


SOURCE_FILES = _discover_source_files()


def test_src_tree_exists_to_check() -> None:
    assert SOURCE_FILES, (
        f"{_SRC_ROOT_ABS} has no .py files -- the token-boundary check has "
        "nothing to walk; this is itself a failure, not a vacuous pass"
    )


@pytest.mark.parametrize(
    "path",
    [p for p in SOURCE_FILES if not _is_sanctioned(p)],
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_file_imports_no_banned_llm_sdk(path: Path) -> None:
    errors = check_file(path)
    assert not errors, "\n".join(errors)


def test_sanctioned_call_site_is_exempt_when_present() -> None:
    """If `nodes/polish.py` exists, it must be excluded from the sweep above
    (it is the one place an LLM SDK import is allowed) -- this test would
    fail loudly if that exemption logic silently stopped matching (e.g. a
    path-separator or `.resolve()` regression), rather than the exemption
    just quietly never firing and every future `polish.py` import failing
    the sweep for the wrong reason.
    """
    sanctioned_abs = REPO_ROOT / SANCTIONED_RELATIVE_PATH
    if not sanctioned_abs.exists():
        pytest.skip("nodes/polish.py does not exist yet (Phase 4 has not landed)")
    assert _is_sanctioned(sanctioned_abs)
    assert sanctioned_abs not in [p for p in SOURCE_FILES if not _is_sanctioned(p)]
