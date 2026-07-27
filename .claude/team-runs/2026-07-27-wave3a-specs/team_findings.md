# Team Findings: Wave 3a

Append immediately, after at most 2 read/search operations. Do not batch.

Format: `### [T-n] <short title>` then what you found, where (file:line or clause id), and what it implies for someone else.

External or fetched documentation goes HERE, never in `team_plan.md` (that file is auto-read by a hook, so untrusted content there amplifies).

---

### [lead] Reconnaissance for this wave

**DEPLOY_SPEC clause disposition (from a full read):**
- Deprecate: DEPLOY-9 (`bridge/auth.py` API-key dependency), DEPLOY-10 (`X-S2S-Key` header), DEPLOY-11 (`hmac.compare_digest`), DEPLOY-12 (key from env via Secret Manager), DEPLOY-14 (401 on mismatch, no allow-if-unset).
- Deprecate: DEPLOY-5 (external HTTPS LB + managed cert + serverless NEG), DEPLOY-6 (`INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER`), DEPLOY-7 (Cloud Armor).
- Amend, do not deprecate: DEPLOY-3 (its `max-instances` text says "gets past Cloud Armor and the API key check"), DEPLOY-8 (its defense-in-depth argument is framed entirely as "API key is identity, Cloud Armor is volumetric").
- **Survive untouched:** DEPLOY-13 (`/health` exemption; its reasoning is auth-mechanism agnostic and its `{"ok","stt","llm","version"}` body was already reviewed as safe to expose), DEPLOY-15 (auth module must not import `rules/`), DEPLOY-17, DEPLOY-18, DEPLOY-19, DEPLOY-20 (minus one grant row), DEPLOY-26.
- DEPLOY_SPEC's Traceability section points at BRIDGE_SPEC and ARCHITECTURE's deprecated clauses. Once DEPLOY-9..15 are themselves deprecated, that pointer needs re-pointing or it becomes a chain to a dead clause.

**BRIDGE_SPEC current state:** v1.1.0. Its CORS line reads "Hosted mode's CORS allowlist is the load balancer's public hostname; see `docs/DEPLOY_SPEC.md`." **DEPLOY_SPEC contains no CORS clause.** That cross-reference has been dangling since Wave 1. The Hosting rewrite makes it moot rather than fixing it, but say so explicitly.

**Static serving:** BRIDGE_SPEC describes `GET /` serving `web/index.html`, "a two-card chooser". That file has never existed on disk. `web/` contains only `clips.html`, `conversation.html` and `README.md`.

**ARCHITECTURE:** v1.1.0. Layer table is orthogonal to auth mechanism and needs no change. The "What is deliberately absent" bullet already carries a Wave 1 `Deprecated` mark naming DEPLOY-9..15.

**Terraform reality (`deploy/terraform/`, 11 files, provider `hashicorp/google ~> 7.0` only):**
- `network.tf` holds 8 resources that the Hosting rewrite retires: regional NEG, Cloud Armor security policy, backend service, url map, managed SSL cert, target HTTPS proxy, global address, global forwarding rule.
- `cloud_run.tf` hardcodes `ingress = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"` as a literal, not a variable.
- Firebase resources need the `google-beta` provider (`google_firebase_project`, `google_firebase_hosting_site`, `google_firebase_web_app`). Not declared today. Adding it does not conflict with existing resources but is net-new provider surface.
- `wif.tf`'s Workload Identity Federation is CI-deploy identity (GitHub Actions to GCP). **Unrelated to end-user auth. Not touched by this change.**

**`pyproject.toml`:** no `firebase-admin`, no `google-auth` as a direct dependency, no `pyjwt`. `google-auth` arrives transitively via `google-cloud-speech` under the `stt-gcp` extra only, which is not a reliable base to build verification on.

**Repo-wide:** zero occurrences of firebase, vite, react, typescript, npm or node. The only hit is prose in `scripts/tasks.py:6` explaining that uv has no npm-style task table.

### [T4] .env.example and pyproject.toml done, committed 8e7e021

**`.env.example`:** added a server-side Firebase Auth section (`FIREBASE_PROJECT_ID`
as the verified audience, `S2S_ALLOWED_EMAIL_DOMAIN=softical.tech` as the
authoritative server-side domain check, client `hd` hint noted as UX only)
and a Vite client-config section (`VITE_FIREBASE_API_KEY`,
`VITE_FIREBASE_AUTH_DOMAIN`, `VITE_FIREBASE_PROJECT_ID`,
`VITE_FIREBASE_APP_ID`, `VITE_FIREBASE_MESSAGING_SENDER_ID`,
`VITE_API_BASE_URL=/api`). The Vite section leads with an explicit
not-a-secret comment: the web API key identifies the project, does not
authorize anything, is compiled into the bundle, and must never go into
Secret Manager or trigger a panic rotation if found in devtools/a bundle.
`S2S_APP_API_KEY` deprecated in place (not deleted), pointing at
DEPLOY_SPEC's new Firebase Auth section superseding DEPLOY-9 through
DEPLOY-14 — **T1: I did not invent a new DEPLOY-n id for the Firebase
clauses since I don't know your numbering; my comment says "DEPLOY_SPEC's
Firebase Auth section" generically. Adjust if you want a specific id
cited.**

**`pyproject.toml`:** confirmed `firebase-admin`/`google-auth`/`pyjwt` were
all absent as direct deps (only `google-auth` arrived transitively via the
`stt-gcp` extra). Chose **`google-auth[requests]>=2.28`** over
`firebase-admin`: `google.oauth2.id_token.verify_firebase_token` (confirmed
via googleapis.dev / google-auth.readthedocs.io reference docs) verifies
audience + issuer + iat/exp against Firebase's public certs and is
sufficient since the bridge only ever verifies ID tokens — it never mints
custom tokens, manages users, or reads Firebase user records, so the full
Admin SDK's extra surface and credential-management stack would be pure
overhead. The `[requests]` extra is required because plain `google-auth`
does not bundle an HTTP transport; `verify_firebase_token` needs
`google.auth.transport.requests.Request`. Put it in a **new
`bridge-auth` optional-dependency group**, not core deps and not folded
into `stt-gcp`, since it's only imported by `src/s2s_harness/bridge` for
the deployed `s2s serve` auth path — CLI, rules engine and graph never
need it. `uv lock` regenerated (80 packages resolved), `uv sync` green.

**Gate output, all real, all green:**
- `uv run lint` -> ruff check: all checks passed; ruff format --check: 21 files already formatted
- `uv run mypy` -> Success: no issues found in 13 source files
- `uv run test-golden` -> 19 passed in 0.11s
- `uv run pytest tests/ -q` -> 51 passed, 1 skipped in 1.75s
- `graphify update .` -> 736 nodes, 1020 edges, 55 communities

Committed path-scoped to `.env.example`, `pyproject.toml`, `uv.lock` only
(did not add `graphify-out/*` or `docs/BRIDGE_SPEC.md`, both already
modified by other teammates concurrently — not mine to commit). Pushed.
SHA `8e7e021`.

---

### [lead] Behaviours the HTML encodes that WEB_SPEC must preserve

From a full read of both artifacts (conversation.html: 202 lines CSS, 470 markup, 649 JS; clips.html: 132/256/460).

1. **The chip DOM-diff guard, `scanSignals()`** (conversation.html:750-779, clips.html:446-471). Builds a signature `found.map(f => (f.box?"1":"0")+f.label).join("|")`, caches it on `host.dataset.sig`, and returns early without touching `innerHTML` when unchanged. The bug it prevents: `recompute()` is bound to document-level `input` AND `change`. Clicking a suggestion chip blurs the notes textarea, which fires `change`, which re-enters render and replaces the chip node before the browser's `click` resolves (a click needs mousedown and mouseup on the same still-present node). The flag never gets set. In React the equivalent is stable `key`s plus memoisation on the same signature. **Specify the invariant, not the mechanism.**
2. **Placeholder highlight:** `gap(t)` returns `"【"+t+"】"`. `hlGaps(t)` does `esc(t).replace(/【([^】]*)】/g, ...)` wrapping each in `<em>`. Escape happens BEFORE the match. CSS `.justbox em{color:var(--warn);background:#2a2415;...}`. The token form is in CLAUDE.md's guarded set.
3. **No debounce exists today.** `recompute()` runs synchronously on every keystroke. BRIDGE_SPEC specifies it becomes a debounced 250ms `POST /evaluate`.
4. **Validation never blocks.** `validate()` output is advisory cards only. No button is disabled by severity. Deliberate: this is a training surface, not a gate.
5. **No localStorage anywhere.** A refresh loses everything. Decide whether that stays true.
6. **Reset restores `turnsA`/`turnsB` to 4**, not 0, and is scoped to `#viewForm` only.
7. **`frag()` (strip trailing `.;,` before splicing) exists in clips.html only.** conversation.html splices `best`/`worst` raw. Asymmetry to resolve.
8. **`creative` is missing** from conversation.html's `scenario_type` select; the schema has 8 values, the select offers 7.
9. **`prompts_used` is `list[str]`** in GRAPH_SPEC but collected as one newline-delimited textarea, never split client-side.
10. **`window.claude.complete` prompt contract** (conversation.html:1250, clips.html:825) is effectively the implicit spec for the server-side polish node: rules digest, per-task block, "skeleton to improve not replace", never invent facts, leave `【like this】` placeholders, first person, 5-9 sentences, no bullets. This path is deleted, but losing that contract silently degrades justification quality with no test to catch it. Wave 3b's `polish.py` should inherit it.
11. **Design tokens** worth carrying: `--bg:#0e1014 --panel:#161a21 --panel2:#1c212a --line:#2a313d --txt:#e7ecf3 --dim:#9aa5b5 --acc:#6ea8fe --warn:#f5c451 --err:#f2777a --ok:#7dd3a0 --a:#7aa2f7 --b:#c98bdb`. Dark theme only, system font stack.
12. Client JS `decide()` returns a `contested` field with no counterpart on the `Verdict` model. Client `validate()` conflates code and label into one short string; `Finding` wants both separately.

---

### [T2] Confirmed dangling CORS reference and non-existent web/index.html; local-mode CORS also changes

Read `docs/BRIDGE_SPEC.md` and `docs/ARCHITECTURE.md` in full (my owned files) plus `docs/DEPLOY_SPEC.md` in full (read-only, to confirm the cross-reference and get exact DEPLOY-n numbers before T1's rewrite lands).

- Confirmed: `docs/DEPLOY_SPEC.md` v1.0.0 has no CORS clause anywhere (8 sections, DEPLOY-1..26, none mention CORS). BRIDGE_SPEC's line "Hosted mode's CORS allowlist is the load balancer's public hostname; see `docs/DEPLOY_SPEC.md`" has been dangling since v1.0.0/Wave 1. Recording this in BRIDGE_SPEC as an explicit note, not silently patching.
- Confirmed: `web/` has no `index.html`; BRIDGE_SPEC's "Static serving" section describing a "two-card chooser" there was never true. Recording as a historical-note callout (not a Deprecated block, since it was never valid) rather than silently rewriting.
- **New finding, not previously listed:** local-mode CORS also needs to change, independent of the hosted-mode same-origin fix. Today's allowlist is `null` (file://) + `http://127.0.0.1:8787`, because the HTML artifacts were opened as local files. Once the HTML retires in favor of a Vite/React SPA, local dev is genuinely cross-origin (`http://localhost:5173` typically talking to `http://127.0.0.1:8787`), so the local allowlist entries change too, not just the hosted ones. Noting for **T3**: BRIDGE_SPEC will state the local CORS allowlist as `http://localhost:5173` pending WEB_SPEC.md confirming the actual local dev port/preview origin(s) it specifies. If WEB_SPEC picks a different port or multiple ports (dev + preview), tell me and I will adjust the allowlist line in BRIDGE_SPEC to match rather than leaving two documents disagree on the port.
- Asked T1 (SendMessage) for the exact new DEPLOY-n ids covering Firebase ID-token verification, `@softical.tech` check, 401/403 split, Hosting-rewrite-as-front-door, and the ingress setting compatible with the Hosting rewrite, since BRIDGE_SPEC's auth block and endpoints section need to cite them precisely rather than guess. Proceeding with the rest of the rewrite in parallel; will slot in exact ids once T1 replies.
- Note on drafting style: BRIDGE_SPEC's auth posture line is *already* a Deprecated block (local "no auth" superseded by the Wave 1 API-key mechanism). This wave deprecates that API-key mechanism itself in favor of Firebase Auth, i.e. a second layer of supersession on the same clause. Flattening this into one clause with an explicit chain (original -> API key, now itself superseded -> Firebase Auth, current) rather than nesting a `Deprecated` block inside a `Deprecated` block, per CLAUDE.md's warning about not creating a maze.

---

### [T2] BRIDGE_SPEC + ARCHITECTURE done; committed as part of a233595, not a standalone SHA

Finished all 5 BRIDGE_SPEC tasks and all 4 ARCHITECTURE tasks from `team_plan.md` Phase B. T1 never replied with the new `DEPLOY-n` ids before I finished, so three blocks (BRIDGE_SPEC's bind-Deprecated bullet, BRIDGE_SPEC's auth-Deprecated bullet, ARCHITECTURE's deliberately-absent-Deprecated bullet) cite the old Wave 1 ids (DEPLOY-5/6/7, DEPLOY-9..15) plus an explicit inline placeholder addressed to T1 ("T1: cite your exact new DEPLOY-n id(s) here once assigned") rather than a guessed number. This matches the pattern T4 already used in `.env.example` for the same gap.

**Process note for the durable record:** staged `docs/ARCHITECTURE.md` and `docs/BRIDGE_SPEC.md` with `git add` intending my own scoped commit, but two heredoc commit attempts failed on a shell quoting error before I could run them. In that window T3 committed `docs/WEB_SPEC.md` and, because the git index is shared across teammates in this working tree (not per-teammate worktrees), T3's commit `a233595` picked up my already-staged changes to both my files along with their own. `git diff HEAD -- docs/BRIDGE_SPEC.md docs/ARCHITECTURE.md` is empty and `git show a233595 --stat` confirms both files with the same line counts I authored, so the content is exactly what I intended, on `origin/main`, just under T3's commit message rather than my own. Recording this so nobody goes looking for a separate T2 SHA that does not exist. **Lesson for later waves: commit immediately after staging, before drafting the commit message, when the working tree is shared.**

- CORS: dangling xref recorded explicitly, hosted-mode CORS eliminated via Hosting rewrite (same-origin), local-mode allowlist changes to `http://localhost:5173` (cross-referencing WEB_SPEC's dev server).
- Static serving: `web/index.html` non-existence recorded as a historical note (not a Deprecated block, since it was never true); bridge is API-only in both modes now; local rater runs the SPA dev server / preview pointed at the bridge.
- Auth Deprecated block: flattened into one chain (local unauthenticated, unaffected -> Wave 1 API key, superseded -> Wave 3a Firebase Auth, current) instead of nesting Deprecated-in-Deprecated.
- Endpoints: added the `Authorization: Bearer <idToken>` requirement note, `GET /health` exemption preserved via original DEPLOY-13 reasoning.
- Migration/Why-keep-the-HTML sections: deprecated together (they're one argument) pointing at `docs/WEB_SPEC.md`, text preserved verbatim below the notice since WEB_SPEC still needs to reproduce that behavior.
- ARCHITECTURE: no-database bullet reaffirmed against Firebase-without-Firestore explicitly; layer-boundary table confirmed unchanged with an explicit note (not left ambiguous); superseded-auth bullet re-chained the same way as BRIDGE_SPEC's.

`graphify update .` run after all edits -> 751 nodes, 1034 edges, 56 communities.

---

### [T2] Final pass complete: real DEPLOY-27..33 ids slotted in, commit 6844b9e

Read `docs/DEPLOY_SPEC.md` v2.0.0 in full (T1 landed it while I was mid-edit) and `docs/WEB_SPEC.md`'s WEB-4 directly (T3's SendMessage named it, confirmed the exact text and both port numbers before citing).

Replaced all three placeholder pointers with real ids:
- BRIDGE_SPEC bind-Deprecated bullet: DEPLOY-6 superseded by **DEPLOY-32** (ingress `all`), front door is **DEPLOY-31**. Added the security consequence lead flagged verbatim: Cloud Run now directly reachable at its `run.app` URL, bypassing Hosting but not auth (DEPLOY-27 runs in application code); auth is now the first and only line of defense, not the last of three. Explicitly said not to describe this as equivalent to Wave 1.
- BRIDGE_SPEC auth-Deprecated bullet: DEPLOY-9/10/11/12/14 superseded by **DEPLOY-27 through DEPLOY-30**; DEPLOY-13 and DEPLOY-15 called out by name as surviving, not folded into the superseded set.
- ARCHITECTURE's deliberately-absent bullet: same DEPLOY-27..33 citations, plus a pointer to the reachability consequence in BRIDGE_SPEC/DEPLOY-8 rather than repeating it a third time.
- Endpoints intro and `GET /health` entry: replaced generic "Firebase Auth clauses (Wave 3a)" with DEPLOY-27 through DEPLOY-30, and "safe to expose without a key" with "without any credential" (the old phrasing assumed a key, which no longer exists).
- CORS local allowlist: now cites `docs/WEB_SPEC.md` WEB-4 by id and both ports (`localhost:5173` dev, `localhost:4173` preview) instead of dev-port-only. Strengthened the asymmetry language per lead's note: hosted has no allowlist (same-origin), local has a two-entry allowlist (genuinely cross-origin), neither generalizes to the other, explicit "do not simplify this away" warning in both directions.

Committed path-scoped to `docs/ARCHITECTURE.md` + `docs/BRIDGE_SPEC.md` only (verified `git status` first this time, per T3's lesson-learned) -> **6844b9e**, pushed to `origin/main` on top of T1's `49645c6`. `graphify update .` re-run, no topology change (docs-only).

---

### [T1] DEPLOY_SPEC v1.0.0 -> 2.0.0 complete; exact new ids for T2's placeholders

Read `team_plan.md`, `team_findings.md` in full, then `docs/DEPLOY_SPEC.md`, `docs/BRIDGE_SPEC.md`, `docs/ARCHITECTURE.md` (the last two to match Wave 1's Deprecated-block voice per the task brief).

**Disposition, matches the lead's recon exactly:** deprecated in place DEPLOY-5, 6, 7, 9, 10, 11, 12, 14 (8 clauses, `grep -c 'Deprecated' docs/DEPLOY_SPEC.md` = 8, verified after fixing two pre-existing generic capital-D mentions in the intro/Traceability prose to lowercase so the count is exact). Amended (not deprecated) DEPLOY-3 and DEPLOY-8, both retaining their original 1.0.0 text verbatim in the clause body for the record. Kept DEPLOY-13 and DEPLOY-15 with re-pointed prose. Edited DEPLOY-16 (two secrets, not three) and DEPLOY-20's grant table (two secret resources, not three). New clauses DEPLOY-27 through DEPLOY-33 in a new section 3a, continuing the existing numbering, nothing renumbered.

**Verification questions, both answered with citations, neither guessed:**
1. **Ingress must be `all`, not `internal-and-cloud-load-balancing`.** GCP's Cloud Run ingress-settings doc (`docs.cloud.google.com/run/docs/securing/ingress`, fetched 2026-07-27) lists Firebase Hosting among services that invoke Cloud Run via the service's default `run.app` URL, and states disabling that URL "prevents [Firebase Hosting] from working as expected." The same page defines `internal-and-cloud-load-balancing` as blocking direct `run.app` access from the internet, admitting only Cloud Load Balancing infrastructure or internal VPC sources. Firebase Hosting's rewrite proxy invokes the public `run.app` URL directly, it is not GCLB infrastructure, so that ingress setting would block the rewrite's own backend calls. DEPLOY-6 (deprecated) is superseded by DEPLOY-32, which carries this citation.
2. **Authorization header preservation through the Hosting rewrite: corroborated, not singularly documented.** No single Firebase doc sentence states "the Authorization header is preserved." What is documented: Firebase strips `Cookie` except `__session`, and lists a specific hop-by-hop header-strip set for Cloud Functions (`Connection`, `Keep-Alive`, `Proxy-Authorization`, `TE`, `Trailer`, `Transfer-Encoding`, `X-Google-*`) that does not include `Authorization`. Separately, `Authorization: Bearer <idToken>` through a Hosting rewrite to Cloud Run/Functions is Google's own commonly documented integration pattern. DEPLOY-32 records this as an admitted gap requiring a live smoke test in Wave 3b/3c, with `X-Serverless-Authorization` named as the documented fallback transport if the header turns out to be altered.

**Conflict caught and fixed before commit:** my first draft of DEPLOY-27 named `firebase-admin` as the verification library, guessed independently before I re-read `team_findings.md` for T4's entry. T4 had already implemented and committed (`pyproject.toml`, SHA `8e7e021`) `google-auth[requests]>=2.28` with `google.oauth2.id_token.verify_firebase_token()` instead, specifically rejecting `firebase-admin` as unnecessary surface since the bridge only verifies tokens and never manages users. Rewrote DEPLOY-27 and DEPLOY-33 to match T4's actual dependency and rationale rather than let the spec contradict what's already in `pyproject.toml`. Lesson recorded here in case another teammate's draft made the same independent guess.

**Security tradeoff:** recorded in the spec body (DEPLOY-8's amendment, not a footnote), not just in this findings file: Cloud Armor's retirement removes per-IP rate limiting and the IP allowlist with no replacement; what remains is `max-instances = 2`, the ID-token check, and Firebase Hosting's edge (CDN/TLS, not a WAF or rate limiter). Explicit operator guidance recorded for if this ever becomes multi-rater or public-facing: reinstate a volumetric control (restore the DEPLOY-5..7 stack, ingress reverted alongside it, or whatever GCP's current recommended Hosting-plus-volumetric-protection integration is at that time) before widening access.

**For T2, exact ids to replace your three placeholders:**
- BRIDGE_SPEC's bind-Deprecated bullet (was citing old DEPLOY-6): DEPLOY-6 is now itself deprecated, pointing to **DEPLOY-32** (required ingress `all`) and **DEPLOY-31** (Hosting rewrite as front door). Cite both; they're the ingress and front-door halves of the same replacement.
- BRIDGE_SPEC's auth-Deprecated bullet (was citing DEPLOY-9..15): DEPLOY-9, 10, 11, 12, 14 are now deprecated, pointing to **DEPLOY-27** (Firebase ID-token verification, header, and library), **DEPLOY-28** (`@softical.tech` server-side check), **DEPLOY-29** (401 vs 403), **DEPLOY-30** (`email_verified` gate). DEPLOY-13 (`/health` exemption) and DEPLOY-15 (no `rules/` import) are unchanged in substance, still current, cite them directly rather than as deprecated.
- ARCHITECTURE's deliberately-absent-Deprecated bullet (same old DEPLOY-9..15 cite): same replacement set as above, **DEPLOY-27 through DEPLOY-30**.
- DEPLOY_SPEC's own Traceability section now documents this as a two-hop chain explicitly (original -> DEPLOY-9..15/DEPLOY-6, now deprecated -> DEPLOY-27..33, current) and asks you to shorten your own two files' pointers to go straight to DEPLOY-27..33 where practical, per the addendum there.

`uv run` gates not applicable, this is a docs-only file with no test surface of its own; `graphify update .` run twice (once after the initial draft, once after the T4-dependency fix), final: 753 nodes, 1036 edges, 56 communities.

Committed path-scoped to `docs/DEPLOY_SPEC.md` only. SHA and push status logged in `team_progress.md`.

---
