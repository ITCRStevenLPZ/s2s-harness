"""Task shims exposed via `[project.scripts]` so `uv run <name>` works.

Background (see team_findings.md [T4] in
.claude/team-runs/2026-07-26-foundations-and-deploy/ for the full trace):

uv has no npm-style task table -- `uv run <name>` only resolves an installed
console script or something already on PATH. `[project.scripts]` entry point
names cannot contain a colon: a wheel build with a name like "test:golden"
fails at build time with "invalid console script" (this is a core-metadata /
wheel restriction, not a uv limitation, and reproduces with any build
backend). That means the literal CLAUDE.md forms `uv run test:golden`,
`uv run test:golden:real` and `uv run test:golden:all` cannot be implemented
as written. The hyphenated names below (`test-golden`, `test-golden-real`,
`test-golden-all`) are the closest working equivalent; `uv run lint` and
`uv run mypy` have no colon and work as specified (`mypy` needs no wrapper at
all -- it is the mypy package's own console script, configured via
`[tool.mypy]` in pyproject.toml).

`tests/golden/` is still empty while the rules engine and fixtures are being
built. pytest's own "no tests collected" exit code (5) is treated as a pass
with a notice so these gates no-op cleanly today and tighten automatically
once fixtures land, per the wave lead's instruction. Any other non-zero exit
(a real failure, or a collected-and-failing test) still fails the gate.
"""

from __future__ import annotations

import os
import subprocess
import sys

PYTEST_NO_TESTS_COLLECTED = 5


def _run(cmd: list[str], env: dict[str, str] | None = None) -> int:
    print(f"+ {' '.join(cmd)}", file=sys.stderr)
    return subprocess.run(cmd, env=env, check=False).returncode


LINT_PATHS = ["src", "tests", "scripts"]


def _lint() -> int:
    # Scoped to owned code directories, not "." -- ruff format also rewrites
    # fenced Python code blocks inside Markdown, which would reach into
    # docs/ and criteria/ (owned by other teammates, criteria/ is guarded).
    check_code = _run(["ruff", "check", *LINT_PATHS])
    format_code = _run(["ruff", "format", "--check", *LINT_PATHS])
    return check_code or format_code


def lint() -> None:
    """`uv run lint` -- ruff check plus ruff format --check, whole repo."""
    raise SystemExit(_lint())


def _pytest_golden(extra_args: list[str], env: dict[str, str]) -> int:
    code = _run(["pytest", "tests/golden", "-q", *extra_args], env=env)
    if code == PYTEST_NO_TESTS_COLLECTED:
        print(
            "no golden fixtures collected yet -- treating as a pass "
            "(tree is still bootstrapping, see EVAL_SPEC.md)",
            file=sys.stderr,
        )
        return 0
    return code


def _test_golden() -> int:
    """Tier 1: null STT, stubbed polish, no network, zero API cost."""
    env = {**os.environ, "S2S_STT_PROVIDER": "null", "S2S_NO_LLM": "1"}
    return _pytest_golden(["-m", "not tier2", "--disable-socket"], env)


def _test_golden_real() -> int:
    """Tier 2: real Anthropic API and real Gemini/GCP speech. Pre-merge only."""
    env = dict(os.environ)
    return _pytest_golden(["-m", "tier2"], env)


def test_golden() -> None:
    """`uv run test-golden` -- Tier 1."""
    raise SystemExit(_test_golden())


def test_golden_real() -> None:
    """`uv run test-golden-real` -- Tier 2. Never weaken this on a 429/quota
    failure: that is "re-run when quota recovers", not a reason to pass."""
    raise SystemExit(_test_golden_real())


def test_golden_all() -> None:
    """`uv run test-golden-all` -- both tiers, Tier 1 first."""
    tier1 = _test_golden()
    tier2 = _test_golden_real()
    raise SystemExit(tier1 or tier2)
