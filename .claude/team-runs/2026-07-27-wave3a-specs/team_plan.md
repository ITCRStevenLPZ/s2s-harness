# Team Plan: Wave 3a — Specs for the React frontend and Firebase Auth

## Goal

Amend the deployment-facing specs so they describe the system the user has chosen: a Vite/React/TSX frontend on Firebase Hosting, Firebase Auth restricted to `@softical.tech` replacing the Wave 1 app-level API key, the FastAPI bridge staying on Cloud Run behind a Firebase Hosting rewrite, and every required credential documented in `.env.example`.

**This wave writes specs only. No React code, no Terraform, no application code.** Waves 3b, 3c and 3d implement against what you write, so an underspecified clause here becomes a guess there.

## Ground rules

1. **Read this file before any major decision.** Your context is volatile; this file is not.
2. **Cite an id in every change.** `DEPLOY-n`, `BRIDGE-n`, `WEB-n`, `CRIT-n`, `RULE-n`, `STATE-n`, `EVAL-n`. New normative statements get new ids continuing existing numbering. **Never renumber an existing id.**
3. **Never delete a requirement.** Obsolete ones are marked `Deprecated` in place with a pointer to the superseding clause, and the document's Version header is bumped. This is CLAUDE.md's deprecation rule and it is absolute. Wave 1 established the pattern; follow its exact style.
4. **Stay inside your file ownership.** Cross-boundary needs go to the owning teammate via SendMessage. If SendMessage is unavailable in your toolset (several agents hit this in earlier waves), broadcast in `team_findings.md` instead and say so.
5. **Write findings to `team_findings.md` immediately**, after at most 2 read/search operations. Do not batch.
6. **Log actions to `team_progress.md`** as you go. Your FINAL action must be `- [T-n] COMPLETE: <summary>`. In earlier waves silence was indistinguishable from success and cost real time.
7. **Do not guess APIs, provider schemas, or platform behaviour.** Verify against current documentation and cite it. A plausible-looking wrong clause is worse than an admitted gap.
8. **No emojis, no em-dashes.**
9. `graphify update .` before marking complete.

## Decisions already made by the user. Do not re-litigate.

| Decision | Choice |
|---|---|
| Auth | Firebase Auth only, replacing `X-S2S-Key`. **No Firestore.** |
| Frontend | Vite + React + TSX on Firebase Hosting; the two HTML files retire |
| Backend | FastAPI stays on Cloud Run |
| Front door | Firebase Hosting rewrite of `/api/**` to Cloud Run |
| Domain lock | Server-side ID-token verification is authoritative; client `hd` hints are UX only |
| Project | One new project serving Hosting, Cloud Run, Secret Manager, Artifact Registry, WIF |
| Users | Single rater. Sign-in is an access gate, not an identity system. |

**Consequence to record honestly:** the Hosting rewrite restores same-origin, so CORS is eliminated rather than reopened. But it retires the Wave 1 load balancer stack (8 `google_compute_*` resources) **and the Cloud Armor policy**. Wave 1 added Cloud Armor deliberately. This is a real reduction in volumetric defence, mitigated only by `max_instances = 2` and Firebase Hosting's edge. Say so plainly in the spec; do not present it as a neutral simplification.

## Current state you are amending

- `docs/DEPLOY_SPEC.md` v1.0.0, DEPLOY-1..26
- `docs/BRIDGE_SPEC.md` v1.1.0, already carries two Wave 1 `Deprecated` blocks
- `docs/ARCHITECTURE.md` v1.1.0, already carries one Wave 1 `Deprecated` bullet
- `.env.example`, 10 variables, `S2S_APP_API_KEY` last
- `pyproject.toml` has **no** token-verification dependency (`firebase-admin`, `google-auth`, `pyjwt` all absent)
- Zero occurrences of Firebase, Vite, React, TypeScript or npm anywhere in the repo
- `web/` holds `clips.html`, `conversation.html`, `README.md`. No `web/index.html` has ever existed despite BRIDGE_SPEC referencing it.

## Team

| Teammate | Owns |
|---|---|
| T1 `deploy-spec` | `docs/DEPLOY_SPEC.md` |
| T2 `bridge-spec` | `docs/BRIDGE_SPEC.md`, `docs/ARCHITECTURE.md` |
| T3 `web-spec` | `docs/WEB_SPEC.md` (new) |
| T4 `env-and-deps` | `.env.example`, `pyproject.toml` |

Do not touch `criteria/`, `src/`, `tests/`, `docs/RULES_SPEC.md`, `docs/GRAPH_SPEC.md`, `docs/EVAL_SPEC.md`, `CLAUDE.md`, or `.claude/settings.json`.

## Phases

### Phase A: DEPLOY_SPEC [T1]
- [ ] Deprecate in place: DEPLOY-9, 10, 11, 12, 14 (shared-secret mechanism); DEPLOY-5, 6, 7 (LB, ingress restriction, Cloud Armor)
- [ ] Amend DEPLOY-3 and DEPLOY-8 (both name the API key or Cloud Armor in their text)
- [ ] Keep DEPLOY-13 and DEPLOY-15, re-pointing their cross-references
- [ ] Remove `s2s-app-api-key` from DEPLOY-16 and DEPLOY-20's grant table
- [ ] New clauses: Firebase ID-token verification, `@softical.tech` server-side check, 401 vs 403, Hosting rewrite as front door, required Cloud Run ingress setting
- [ ] **Verify against current docs** whether a Hosting rewrite works with `INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER`. Cite the source.

### Phase B: BRIDGE_SPEC + ARCHITECTURE [T2]
- [ ] CORS section: same-origin, no allowlist in hosted mode. Note the dangling cross-reference to a DEPLOY_SPEC CORS clause that never existed.
- [ ] Static-serving section rewritten; `web/index.html` never existed
- [ ] Update the existing `Deprecated` auth block naming `X-S2S-Key` and DEPLOY-9..15
- [ ] ARCHITECTURE: same superseded bullet re-pointed; layer table unchanged

### Phase C: WEB_SPEC [T3]
- [ ] New file, `WEB-n` ids, Version 1.0.0
- [ ] Chip DOM-diff guard as an **invariant**, not an implementation
- [ ] `【...】` token, regex, and escape-before-match ordering as normative
- [ ] Validation advisory-only, never blocking
- [ ] Suggestions come from the server, not a client regex table
- [ ] Mode deltas, design tokens, auth gate UX
- [ ] Three pre-existing defects recorded for decision, not silently fixed
- [ ] State whether draft survives a refresh

### Phase D: env and deps [T4]
- [ ] Vite client vars, server vars, `S2S_APP_API_KEY` deprecated in place
- [ ] State explicitly that the Firebase web API key is NOT a secret
- [ ] Add a token-verification dependency, regenerate `uv.lock`

## Current Status

- Phase 3 complete at 84226c4, all gates green, 19 fixtures, `{EVAL-24}` met
- Phases A-D: pending
