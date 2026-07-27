"""Pre-commit hook: fail if `src/s2s_harness/rules/` or `src/s2s_harness/models/`
import an LLM SDK, a networking library, or a local I/O library -- CLAUDE.md
design rule 1 (amended Wave 3b, 2026-07-27), the same boundary
`docs/RULES_SPEC.md` states as "every function in this spec is pure -- no
I/O, no clock, no randomness, no model."

This is the fast, dependency-free pre-commit form of the check.
`tests/test_token_boundary.py` (owned by T5 for this wave) is the
authoritative pytest version this mirrors; `token-auditor`'s grep sweep is a
third, independent implementation of the same invariant. All three existing
is intentional defense in depth, not duplication to clean up.

WAVE 3B REWORK -- read this before changing BANNED_MODULES or PURE_DIRS.

This check used to assert the opposite shape of restriction: "only
`src/s2s_harness/nodes/polish.py` may import an LLM SDK," i.e. every file
in the tree except one was checked, and the one exemption carried the whole
weight of the invariant. CLAUDE.md design rule 2 (the single-call-site
invariant) is deprecated in place: LLM code now lives throughout
`src/s2s_harness/llm/` (see `src/s2s_harness/llm/client.py`,
`src/s2s_harness/llm/providers/openrouter.py`,
`src/s2s_harness/llm/providers/gemini.py`) and is called from four roles
(`interpret`, `suggest`, `judge`, `polish`), not one.

The check below is a WEAKER claim than before -- almost all of `src/` is now
unrestricted, including `src/s2s_harness/llm/`, `src/s2s_harness/nodes/`,
`src/s2s_harness/stt/` (which legitimately imports `google-genai` and
`google-cloud-speech` for transcription), the CLI and the bridge. It is
still worth having, because it is still the claim that actually matters:
`PURE_DIRS` below (`rules/`, `models/`) must never import an LLM SDK, make a
network call, or perform I/O, because that purity is what keeps Track A's
verdict deterministic and reproducible. Someone "fixing" a rules-engine bug
by asking a model instead of fixing `docs/RULES_SPEC.md` and the code would
silently break that -- and would not fail any existing golden fixture,
since fixtures assert verdicts, not what produced them. This check is what
catches that failure mode instead.

`BANNED_MODULES` covers three things, not just "LLM SDK":

- the two LLM SDKs this project uses: `openai` (OpenRouter goes through the
  OpenAI SDK with a custom `base_url`, see `providers/openrouter.py`) and
  `google` (Gemini AI Studio via `google-genai`, imported as
  `google.genai`, see `providers/gemini.py`) -- plus the deprecated
  `anthropic` entry (CLAUDE.md rule 2, `pyproject.toml`'s `polish` extra),
  kept banned rather than removed;
- networking libraries (`requests`, `httpx`, `grpc`, `aiohttp`, `urllib3`,
  `socket`), since `google-genai`, `google-cloud-speech` and `google-auth`
  all sit on top of one of these or `google` itself;
- local I/O libraries (`sounddevice`, `soundfile`) for audio hardware and
  file access.

`google` is banned at the bare top-level package rather than just
`google.genai`, because `google-cloud-speech` (used legitimately in
`src/s2s_harness/stt/`) and `google-auth` (the `bridge-auth` extra) share
the same top-level package. Scoping the ban to `PURE_DIRS` rather than
trying to allow-list which `google` submodule is "the LLM one" is exactly
why this directory-based scoping is simpler and more correct than the old
single-file one.

Known limitation, stated rather than silently accepted: this is a static
AST import walk. It proves the absence of a banned top-level import in
`PURE_DIRS`, not the absence of all possible non-determinism -- a dynamic
`importlib.import_module("openai")`, a call routed through a module not in
`BANNED_MODULES`, or non-import I/O (e.g. the `open()` builtin) would not
be caught here. Defense in depth (this script, its pytest mirror,
`token-auditor`'s grep, and human review under the `criteria-keeper` /
`rules-engine-dev` roles) is the actual guarantee, not any single layer.

`src/s2s_harness/rules/` and `src/s2s_harness/models/` may not exist yet on
a from-scratch checkout before Phase 2/3 lands. Their absence is not an
error here: the check simply has nothing to walk until they exist.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

BANNED_MODULES = {
    # LLM SDKs
    "openai",
    "google",  # covers google.genai (Gemini) and google.cloud.speech /
    # google.auth -- banned at the top level on purpose, see module
    # docstring for why a submodule allow-list would be the wrong fix.
    "anthropic",  # deprecated (CLAUDE.md design rule 2); the `polish`
    # extra in pyproject.toml still carries this dependency name, not
    # deleted, per the deprecation rule -- kept banned here to match.
    # Networking
    "requests",
    "httpx",
    "grpc",
    "aiohttp",
    "urllib3",
    "socket",
    # Local I/O
    "sounddevice",
    "soundfile",
}

PURE_DIRS = (
    Path("src/s2s_harness/rules"),
    Path("src/s2s_harness/models"),
)
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
                f"{path}:{node.lineno}: imports '{banned}' -- "
                "src/s2s_harness/rules/ and src/s2s_harness/models/ must stay "
                "free of LLM SDKs, network calls, and I/O (CLAUDE.md design rule 1)"
            )
    return errors


def _is_pure_scope(path: Path) -> bool:
    try:
        relative = path.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        relative = path
    return any(pure_dir in relative.parents for pure_dir in PURE_DIRS)


def main(argv: list[str]) -> int:
    if not SRC_ROOT.exists():
        print("src/s2s_harness/ does not exist yet -- nothing to check")
        return 0

    candidates = [Path(a) for a in argv] if argv else sorted(SRC_ROOT.rglob("*.py"))
    files = [p for p in candidates if p.is_file() and p.suffix == ".py" and _is_pure_scope(p)]

    errors: list[str] = []
    for path in files:
        errors.extend(check_file(path))

    if errors:
        print("Token-boundary violation:")
        for error in errors:
            print(f"  {error}")
        return 1

    print(f"token-boundary check: {len(files)} file(s) clean under rules/ and models/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
