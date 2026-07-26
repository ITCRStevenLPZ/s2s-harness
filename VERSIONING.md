# Versioning

## Scheme

[Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html):
`MAJOR.MINOR.PATCH`.

The single source of truth is `[project] version` in `pyproject.toml`. It is
not duplicated anywhere:

- `s2s --version` reads it at runtime via
  `importlib.metadata.version("s2s-harness")`. `cli-dev` must not add a
  second copy as a Python constant; a hardcoded string drifts from
  `pyproject.toml` the first time someone bumps one and forgets the other.
- `GET /health` (owned by `bridge-dev`, `docs/BRIDGE_SPEC.md`) returns a
  `version` field using the same mechanism, for the same reason.
- Git tags are `vX.Y.Z`, matching `pyproject.toml` exactly (tag `v0.2.0` for
  version `0.2.0`, not `v0.2.0-rc1` unless the release genuinely is a
  pre-release).

## What bumps which number

This project has one deterministic engine (`src/s2s_harness/rules/`) whose
observable behavior is a contract with the rater and with `criteria/`. That
contract, not the usual "public API" framing, is what versioning tracks
here.

- **MAJOR** -- a change to `criteria/`, the hierarchy walk, the threshold
  gate, the error-cluster catalogue, the audio-tolerance rule, the scenario
  inversion rule, or the justification contract that changes an existing
  golden fixture's expected verdict, findings, or draft content (a
  "golden-flip", per CLAUDE.md's golden-flip rule). Also: any change to the
  CLI's command surface or `--json` output shape that breaks an existing
  caller, or a change to the `/evaluate` bridge contract.
- **MINOR** -- new functionality that does not change any existing golden
  fixture's expected output: a new error cluster, a new scenario type, a new
  CLI command or flag, a new STT provider, new bridge endpoints.
- **PATCH** -- bug fixes, dependency bumps, documentation, CI/tooling
  changes, and anything in this file's own governance (workflow pinning,
  pre-commit hook versions) that does not change engine behavior.

A version bump is not required for changes confined to `docs/`,
`.claude/`, or `graphify-out/` alone, unless the change also touches
`criteria/` (see the deprecation rule in CLAUDE.md: criteria changes always
carry a `Version` header bump on the spec file itself, independent of the
package's own SemVer number).

## Release procedure

1. Confirm `uv run lint`, `uv run mypy`, and `uv run test-golden-all` are
   green on `main` (both tiers -- see CLAUDE.md's two-tier test gate; a
   release is a merge-to-main event's downstream consequence, so it
   inherits that gate).
2. Bump `[project] version` in `pyproject.toml` in a normal PR, following
   the rule above. Move the `[Unreleased]` section of `CHANGELOG.md` under a
   new `## [X.Y.Z] - YYYY-MM-DD` heading in the same PR.
3. Once that PR merges to `main`, tag the merge commit:
   `git tag vX.Y.Z && git push origin vX.Y.Z`.
   Any maintainer with push access to `main` may tag; this is not
   restricted to a single role, but the tag must point at a commit that has
   already passed both CI tiers as a normal PR merge -- never tag a commit
   that skipped review.
4. Pushing a `vX.Y.Z` tag triggers `.github/workflows/release.yml`, which
   builds the container image and pushes it to Google Artifact Registry via
   Workload Identity Federation (no long-lived service-account key), tagged
   with **both** the SemVer version and the commit SHA it was built from:
   `<image-path>:X.Y.Z` and `<image-path>:<full-commit-sha>`. Both tags
   point at the same image digest. The exact Artifact Registry path is
   owned by `gcp-deploy` (`docs/DEPLOY_SPEC.md`); this file only fixes the
   tag *format*, coordinated with `gcp-deploy` in Wave 1.
5. `release.yml` deploys to Cloud Run by digest, not by tag, so a later
   retag can never silently change what is running.

## Pre-1.0 note

While the project is spec-only or pre-Phase-3 (the engine not yet
implemented and green against the golden suite), MINOR bumps may include
what would later count as a MAJOR change, per the SemVer §4 pre-1.0
allowance. This relaxation ends the moment `docs/BUILD_PLAN.md` Phase 3 is
marked done.
