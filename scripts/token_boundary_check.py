"""Pre-commit hook: fail if any LLM SDK is imported anywhere under
src/s2s_harness/ except src/s2s_harness/nodes/polish.py -- the single
sanctioned LLM call site (CLAUDE.md design rule 2, docs/EVAL_SPEC.md
"Token-boundary test").

This is the fast, dependency-free pre-commit form of the check.
tests/test_token_boundary.py (owned by rules-engine-dev / eval-runner) is
the authoritative pytest version this mirrors; token-auditor's grep sweep
is a third, independent implementation of the same invariant. All three
existing is intentional defense in depth, not duplication to clean up.

src/s2s_harness/nodes/polish.py does not exist yet (GRAPH-* Phase 4 has not
landed). Its absence is not an error here: the exemption path for it simply
never triggers, so every LLM import found anywhere under src/s2s_harness/
is flagged until the sanctioned file exists to carry them.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

BANNED_MODULES = {"anthropic", "openai"}
SANCTIONED_RELATIVE_PATH = Path("src/s2s_harness/nodes/polish.py")
SRC_ROOT = Path("src/s2s_harness")


def _banned_module(node: ast.AST) -> str | None:
    if isinstance(node, ast.Import):
        for alias in node.names:
            top = alias.name.split(".")[0]
            if top in BANNED_MODULES:
                return top
    elif isinstance(node, ast.ImportFrom) and node.module:
        top = node.module.split(".")[0]
        if top in BANNED_MODULES:
            return top
    return None


def check_file(path: Path) -> list[str]:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{path}: could not read ({exc})"]
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return [f"{path}: could not parse ({exc})"]
    errors = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Import | ast.ImportFrom):
            continue
        banned = _banned_module(node)
        if banned:
            errors.append(
                f"{path}:{node.lineno}: imports '{banned}' -- only "
                f"{SANCTIONED_RELATIVE_PATH} may import an LLM SDK"
            )
    return errors


def _is_sanctioned(path: Path) -> bool:
    try:
        relative = path.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        relative = path
    return relative == SANCTIONED_RELATIVE_PATH


def main(argv: list[str]) -> int:
    if not SRC_ROOT.exists():
        print("src/s2s_harness/ does not exist yet -- nothing to check")
        return 0

    candidates = [Path(a) for a in argv] if argv else sorted(SRC_ROOT.rglob("*.py"))
    files = [p for p in candidates if p.is_file() and p.suffix == ".py" and not _is_sanctioned(p)]

    errors: list[str] = []
    for path in files:
        errors.extend(check_file(path))

    if errors:
        print("Token-boundary violation:")
        for error in errors:
            print(f"  {error}")
        return 1

    print(f"token-boundary check: {len(files)} file(s) clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
