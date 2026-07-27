# Team Plan: Wave 1 — Foundations, CI/CD, and GCP deployment layer

## Goal

Deliver BUILD_PLAN Phases 1-2, fix the six governance defects that make the build plan's own gates unsatisfiable, and author (never apply) a secured GCP Cloud Run deployment layer with GitHub Actions CI/CD, pre-commit, and SemVer versioning.

## Ground rules for every teammate

1. **Read this file before any major decision.** Your context is volatile; this file is not.
2. **Cite a spec ID in every deliverable.** `RULE-n`, `STATE-n`, `GRAPH-n`, `STT-n`, `CLI-n`, `BRIDGE-n`, `WEB-n`, `CRIT-n`, `DEPLOY-n`, `EVAL-n`. If no ID exists for what you are building, that is a spec bug: report it in `team_findings.md`, do not invent behavior.
3. **Stay inside your file ownership.** Overlapping writes cause overwrite races. Cross-boundary needs go to the owning teammate via SendMessage, never by editing their files and never relayed through the lead.
4. **Write findings to `team_findings.md` immediately**, after at most 2 search/read operations. Do not batch.
5. **Log actions to `team_progress.md`** as you go.
6. **Run `graphify update .` before marking any task complete.** This is the definition of done, not a nicety.
7. **Do not use emojis or em-dashes** in code, comments, specs, or docs. Project house rule.
8. **Spanish and English both matter.** Any scanner pattern, phrase hint, or fixture must cover both.
9. **3-Strike protocol.** Two failed attempts, log both and try a different method. Third failure, message the lead.
10. **Nothing is applied to GCP.** `terraform validate` and `terraform plan` only. No `terraform apply`. No `gcloud` command that mutates cloud state.

## Non-negotiable design rules (from CLAUDE.md)

- The rules engine contains **zero LLM calls**. Pure deterministic Python.
- Exactly **one sanctioned LLM call site**: `src/s2s_harness/nodes/polish.py`. Not built in this wave. Do not create a second.
- The deterministic draft is **always** produced. `--no-llm` must yield complete output.
- **Never invent observations.** Missing detail becomes the exact placeholder form `【what the rater must add】`.
- Criteria live in `criteria/`, **not in code**. No magic literals in `src/s2s_harness/rules/`.
- No network calls in `src/s2s_harness/rules/`. No bare dicts crossing a node boundary. Type everything.

## Team Composition

| Teammate | Role | Owns | Model |
|---|---|---|---|
| lead (orchestrator) | Coordination, criteria review (read-only), post-flight | nothing | Opus |
| T1 `criteria-keeper` | Spec IDs, versions, invariant fix | `criteria/`, `docs/{RULES,GRAPH,EVAL,CLI,STT}_SPEC.md`, `docs/BUILD_PLAN.md` | Sonnet |
| T2 `rules-engine-dev` | Catalogues, mode profiles | `src/s2s_harness/rules/` | Sonnet |
| T3 `graph-architect` | State schema | `src/s2s_harness/models/` | Sonnet |
| T4 `ci-dev` | Git remote, CI/CD, pre-commit, versioning | `pyproject.toml`, `.pre-commit-config.yaml`, `.github/`, `CHANGELOG.md`, `VERSIONING.md`, `CODEOWNERS` | Sonnet |
| T5 `gcp-deploy` | Container, Terraform, deploy spec | `Dockerfile`, `.dockerignore`, `deploy/`, `docs/DEPLOY_SPEC.md`, `docs/BRIDGE_SPEC.md`, `docs/ARCHITECTURE.md` | Sonnet |

**File ownership is disjoint by construction.** Note the docs split: T1 owns the engine-facing specs, T5 owns the deployment-facing specs (`BRIDGE_SPEC`, `ARCHITECTURE`, `DEPLOY_SPEC`). Neither touches the other's.

## The six governance defects being fixed

| # | Defect | Owner |
|---|---|---|
| 1 | Spec-ID scheme does not exist anywhere in `docs/` or `criteria/` | T1 (engine specs), T5 (deploy specs) |
| 2 | `uv run lint`/`mypy`/`test:golden*` undefined; `mypy` not a dependency | T4 |
| 3 | `RULES_SPEC` §7 has 6 invariants; `BUILD_PLAN.md:34` says 7 | T1 |
| 4 | No spec carries a `Version` header, yet the deprecation rule bumps one | T1, T5 |
| 5 | `criteria-keeper` pinned to Opus (FIXED in Wave 0) | done |
| 6 | `Transcript` referenced in `GRAPH_SPEC` §1 but never defined | T1 |

## Known correction

`graphify init` **does not exist** in the installed CLI. Use `graphify update .` alone; it bootstraps from cold. CLAUDE.md is wrong on this point. Do not edit CLAUDE.md.

## Phases

### Phase 1: Spec traceability [T1]
- [ ] Add `Version: 1.0.0` header to every spec T1 owns
- [ ] Retrofit `CRIT-n` per `##` heading in `project-criteria.md`; `CRIT-10.1..10.5` for the Justification contract sub-clauses
- [ ] Retrofit `RULE-n`, `STATE-n`, `GRAPH-n`, `CLI-n`, `STT-n`, `EVAL-n` additively. No requirement text reworded.
- [ ] Resolve the 6-vs-7 invariant discrepancy, recording the reason
- [ ] Define `Transcript` in `GRAPH_SPEC` §1
- [ ] Add `--version` to the `CLI_SPEC` global-options table when T4 sends the contract
- **Status:** pending
- **Gate:** all `criteria/` output is reviewed read-only by the lead. Lead approves or rejects with reasons; T1 revises.

### Phase 2: Catalogues [T2] — BUILD_PLAN Phase 1
- [ ] `src/s2s_harness/rules/catalog.py`: 9 error clusters, 4 threshold-utility, 5 threshold-audio, keys and display strings verbatim from `RULES_SPEC` §1
- [ ] `scored_as="naturalness"` on `robotic_intonation` and `over_structured` ONLY
- [ ] Mode profiles selecting entries for `conversation` vs `clips`
- **Done when:** every display string reads correctly spliced into `"{Side} had {display}"`
- **Status:** pending

### Phase 3: State schema [T3] — BUILD_PLAN Phase 2
- [ ] `src/s2s_harness/models/state.py`: 8 Literal aliases, all models from `GRAPH_SPEC` §1
- [ ] Validators: non-negative turns; flag keys exist in T2's catalogue; derived fields rejected on input
- **Done when:** `EvaluationState` round-trips through JSON losslessly and rejects an unknown flag key
- **Status:** pending (soft dependency on T2's catalogue key names)

### Phase 4: Repo gates and versioning [T4]
- [ ] `pyproject.toml`: define `lint`, `mypy`, `test:golden`, `test:golden:real`, `test:golden:all`; add `mypy` to dev deps
- [ ] SemVer, single source of truth in `[project] version`
- [ ] `.pre-commit-config.yaml`, `.github/workflows/{ci,tier2,release}.yml`
- [ ] `gh repo create`, push, branch protection requiring both tiers green
- **Status:** pending

### Phase 5: Deploy layer [T5]
- [ ] `docs/DEPLOY_SPEC.md` with `DEPLOY-n` IDs
- [ ] Amend `BRIDGE_SPEC` and `ARCHITECTURE` in place, marking superseded clauses `Deprecated`, bumping Versions. Delete nothing.
- [ ] `Dockerfile`, `.dockerignore`, `deploy/terraform/`
- [ ] `docker build`, `terraform validate`, `terraform plan` all green
- **Status:** pending

## Current Status

- Wave 0: complete. Commit `1b94755`, graph at 242 nodes / 214 edges.
- Phases 1-5: pending
