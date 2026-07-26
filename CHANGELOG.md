# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
See `VERSIONING.md` for what this project counts as a major, minor, or patch
change, and the release procedure.

## [Unreleased]

### Added

- Executable definition-of-done: `uv run lint`, `uv run mypy`,
  `uv run test-golden`, `uv run test-golden-real`, `uv run test-golden-all`.
  Note the hyphens: `uv run test:golden` as written in CLAUDE.md cannot be
  implemented (colon-containing `[project.scripts]` names are rejected at
  wheel-build time by the Python packaging spec, independent of the build
  backend). See `VERSIONING.md` and `team_findings.md` for the trace.
- `[build-system]` (hatchling) so the local `s2s_harness` package, and every
  gate that depends on it being installed, actually builds.
- `mypy` as a strict-configured dev dependency (`disallow_untyped_defs`,
  `disallow_incomplete_defs`, `warn_return_any`, `strict_equality`,
  `warn_unused_ignores`, `no_implicit_optional`).
- `.pre-commit-config.yaml`: ruff check/format, mypy, gitleaks (Docker
  variant), check-added-large-files, check-yaml, check-toml,
  end-of-file-fixer, trailing-whitespace, plus two local project hooks --
  a token-boundary AST check (no LLM SDK import outside
  `src/s2s_harness/nodes/polish.py`) and Tier 1 golden fixtures on any
  change under `src/s2s_harness/rules/`.
- `.github/workflows/ci.yml`, `tier2.yml`, `release.yml`.
- `CODEOWNERS`, requiring review on the guarded set (`criteria/`,
  `tests/golden/`).

### Fixed

- `uv run lint` / `uv run mypy` / `uv run test:golden*` were named as merge
  gates in CLAUDE.md but did not exist: no `[project.scripts]` entries, no
  task runner, and `mypy` was not even a declared dependency. Every wave's
  definition of done was unrunnable until this change.

## [0.1.0] - 2026-07-26

Specification-only baseline. `criteria/`, `docs/`, `.claude/agents/`, and
the two standalone `web/` HTML artifacts exist; `src/s2s_harness/` holds no
implementation yet beyond what later entries in this file describe.
