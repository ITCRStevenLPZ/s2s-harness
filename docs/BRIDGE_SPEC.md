# Bridge specification

Version: 2.0.0
Last updated: 2026-07-27

`s2s serve` runs a small FastAPI app on `127.0.0.1:8787` exposing the shared engine as an HTTP API. As of v2.0.0 the bridge is API-only in both local and hosted modes — it does not serve any HTML or SPA assets itself. See "Static serving" below for what replaced the two-card static root, and `docs/WEB_SPEC.md` (new, T3, Wave 3a) for the frontend that now calls this API.

This describes local usage. As of v1.1.0 the bridge can also run as a hosted Cloud Run service; where that mode's requirements differ from local `s2s serve`, `docs/DEPLOY_SPEC.md` governs and is called out below. Local `s2s serve` is unchanged by the existence of the hosted mode. As of v2.0.0, the hosted front door is a Firebase Hosting rewrite rather than a load balancer, and hosted-mode auth is Firebase ID-token verification rather than an app-level API key; both changes are called out in place below rather than silently updated.

## Why keep the HTML at all (superseded)

**Deprecated (Wave 3a; superseded by `docs/WEB_SPEC.md`, T3, new in this wave).** This section and "Migration of the existing artifacts" below originally argued for reusing `web/conversation.html` and `web/clips.html` as thin front ends over this API, on the grounds that their forms were already built and tested and only their duplicated rules-engine JavaScript needed to go. That reasoning is superseded, not wrong for its time: the user has since chosen a Vite/React/TSX SPA on Firebase Hosting instead of evolving the two HTML files in place. The two original sections are preserved below, unedited except for this notice, because `docs/WEB_SPEC.md` must still reproduce every behavior they describe (the chip DOM-diff guard, the `【placeholder】` highlighting, the debounced live-evaluate call, the single server-side polish call site) — they are the closest thing that behavioral spec has to prior art, not dead text to skip past.

The forms are already built, already tested against the four worked examples, and the checkbox grid is a genuinely better input surface than sequential terminal prompts when you are flagging a dozen items. What must not survive is the **duplicated rules engine** — two implementations of the hierarchy walk will drift, and the drift will be silent.

So: keep the markup, delete the logic.

## Migration of the existing artifacts (superseded)

**Deprecated (Wave 3a; superseded by `docs/WEB_SPEC.md`).** See the notice above. `web/conversation.html` and `web/clips.html` are not migrated in place; they retire, and the SPA in `docs/WEB_SPEC.md` reimplements the behavior this section specifies as a fresh React component tree.

`web/conversation.html` and `web/clips.html` are the current artifacts with these changes:

1. Delete `decide`, `validate`, `build`/`buildJustification`, and the scanner tables from the inline `<script>`.
2. Keep all markup, styling, chip rendering, and the DOM-diff guard that prevents a blur-triggered re-render from eating a chip click.
3. Replace `recompute()` with a debounced (250 ms) `POST /evaluate`, rendering the response.
4. Keep the `【placeholder】` highlighting — it now highlights markers produced server-side.
5. Delete the `window.claude.complete` path. Polishing happens server-side at the single sanctioned call site.

Net effect: the browser holds form state and rendering only. One engine, one set of rules, one place to fix a bug.

## Endpoints

Every endpoint below except `GET /health` requires an `Authorization: Bearer <idToken>` header carrying a Firebase ID token in the hosted deployment; the server verifies it per `docs/DEPLOY_SPEC.md`'s Firebase Auth clauses (Wave 3a). `GET /health` stays exempt — see that endpoint's entry below and `docs/DEPLOY_SPEC.md` DEPLOY-13, which survives Wave 3a unchanged because its reasoning (an LB or Hosting health check and the front end's availability badge both need unauthenticated reach, and the response body is safe to expose) is auth-mechanism agnostic. Local `s2s serve` requires no header at all, per its unchanged unauthenticated posture below. This section does not redesign the five endpoint shapes themselves; `BUILD_PLAN.md` Phase 7 implements them as specified here.

### `POST /evaluate`
Body: `EvaluationState` fields as JSON (`context`, `a`, `b`, `picks`, `llm_enabled`).
Runs `scan → normalize → decide → audit → draft`, and `polish` only when `llm_enabled` is true and no blocking error exists.
Returns:

```json
{
  "verdict":     {"overall": "A", "driver": "…", "gated": true, "gated_side": "B", "trace": ["…"]},
  "findings":    [{"severity": "error", "code": "…", "label": "AUDIO", "message": "…"}],
  "suggestions": [{"side": "A", "target": "embodied", "kind": "error_cluster", "evidence": "…"}],
  "recommended": {"audio": "B", "overall": "A"},
  "draft":       "I prefer …",
  "polished":    "",
  "llm_skipped_reason": "blocking errors present"
}
```

Because the deterministic path costs nothing, this endpoint can safely be called on every keystroke-debounce — which is what makes the live-updating panel behave the same as it does today.

### `POST /polish`
Explicit, user-initiated polish for the "Generate with AI assist" button. Separating it from `/evaluate` means typing never triggers a model call. Returns 409 with the finding list when blocking errors exist.

### `POST /transcribe`
Multipart audio + `side`. Returns a `Transcript`. Lets the browser offer dictation with the same provider as the CLI.

### `GET /criteria/{topic}`
Serves `criteria/` as JSON so the cheat sheet in the HTML is rendered from the source of truth rather than duplicated in markup.

### `GET /health`
`{"ok": true, "stt": "gemini", "llm": true, "version": "0.1.0"}` — lets the page show the same availability badge the artifacts show today. `version` is read at runtime via `importlib.metadata.version("s2s-harness")`, the same mechanism `s2s --version` uses (single source of truth: `[project] version` in `pyproject.toml`, see `VERSIONING.md`) — never a hardcoded copy. See `docs/DEPLOY_SPEC.md` DEPLOY-13 for why this endpoint stays unauthenticated in the hosted deployment and why that response body, including `version`, is safe to expose without a key.

## Security posture

- **Local `s2s serve` (default, unchanged):** Bind `127.0.0.1` only. Never `0.0.0.0`.
- **Deprecated (local-only scope; superseded for hosted deployment).** Originally: "Bind `127.0.0.1` only. Never `0.0.0.0`" applied unconditionally. It still applies to local `s2s serve` without qualification — nothing about local usage changed. For the hosted Cloud Run deployment, the container binds `0.0.0.0:$PORT` as Cloud Run requires; it is never directly reachable at its `*.run.app` URL. This front door has itself been revisited once, and the chain below is the whole history — follow it once, not as nested archaeology:
  1. **Wave 1:** ingress restricted to `internal-and-cloud-load-balancing` (`INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER`), so every external request traversed an external HTTPS load balancer, per the original DEPLOY-6.
  2. **Wave 3a, current:** that load balancer front door (DEPLOY-5/6/7: the LB itself, that ingress setting, and Cloud Armor) is deprecated in `docs/DEPLOY_SPEC.md` in favor of a Firebase Hosting rewrite of `/api/**` to the Cloud Run service, with whichever Cloud Run ingress setting `docs/DEPLOY_SPEC.md`'s network-posture section specifies as compatible with a Hosting rewrite — verified there against current GCP documentation, not re-derived here. *(T1: cite your exact new `DEPLOY-n` id(s) here in place of this description once assigned; flagged to you directly and in `team_findings.md`.)*
- **CORS.** This bullet has read "Hosted mode's CORS allowlist is the load balancer's public hostname; see `docs/DEPLOY_SPEC.md`" since v1.0.0. **That cross-reference has been dangling for the entire life of this document: `docs/DEPLOY_SPEC.md` has never contained a CORS clause.** Recorded here explicitly, not quietly patched, because an unnoticed dangling reference is exactly the kind of defect that recurs when the fix is silent instead of named (confirmed by re-reading all of DEPLOY-1 through DEPLOY-26 in Wave 3a; none mention CORS).

  The Hosting rewrite happens to make the dangling reference moot rather than requiring a real fix: Firebase Hosting rewrites `/api/**` to the Cloud Run service, so the browser loads the SPA and calls the API from the same origin (the Hosting domain). Same-origin requests are not subject to CORS at all — no preflight, no `Access-Control-*` response headers, no allowlist to maintain, in the hosted configuration. This restores, for the hosted case, the same-origin property this document's now-superseded "Static serving" section originally valued ("Serving them from the same origin as the API avoids CORS entirely") — the mechanism changed from "FastAPI serves the HTML" to "Hosting rewrites to FastAPI", but the same-origin property it produces is the same one, not a reopened cross-origin split.

  Local mode still needs a real CORS allowlist, and that allowlist changes independently of the hosted fix above: local development is genuinely cross-origin now that the SPA replaces file:// HTML. The SPA's local dev server (`vite dev`, default `http://localhost:5173`, see `docs/WEB_SPEC.md`) is a different origin than the bridge (`http://127.0.0.1:8787`). The local allowlist is therefore `http://localhost:5173` (plus any additional local preview origin `docs/WEB_SPEC.md` specifies), replacing the old `null` (file://) entry now that file-opened HTML no longer exists.
- **Deprecated (local-only scope; superseded for hosted deployment).** Originally (v1.0.0): "No auth — the surface is loopback-only and single-user. Do not add remote deployment without revisiting this." Local `s2s serve` remains correctly unauthenticated — a loopback bind on a single-user machine has no one to authenticate against; nothing about that has ever changed. The hosted deployment's auth mechanism has itself been revisited once since. Recorded as one chain, not a Deprecated block nested inside a Deprecated block, so a reader follows one path instead of an archaeology dig:
  1. **Wave 1:** an app-level shared-secret API key — `X-S2S-Key` header, `hmac.compare_digest` comparison, `GET /health` exempt — specified in the original DEPLOY-9 through DEPLOY-15.
  2. **Wave 3a, current:** that shared-secret mechanism is itself deprecated in `docs/DEPLOY_SPEC.md` in favor of Firebase ID-token verification: `Authorization: Bearer <idToken>` checked server-side against the Firebase project's audience and the `@softical.tech` domain, with `GET /health` still exempt — the original DEPLOY-13 reasoning survives unchanged, since it was always auth-mechanism agnostic (an LB or Hosting health check and the front end's availability badge both need unauthenticated reach, and the response body was already reviewed as safe to expose). *(T1: cite your exact new `DEPLOY-n` id(s) for ID-token verification, the domain check, and the 401 vs 403 split here once assigned; flagged to you directly and in `team_findings.md`.)*

  Do not treat the Wave 1 shared-secret mechanism as still live when reading this bullet — it is superseded, not one of two current options.
- No request logging of note content by default; `--log-notes` opts in for debugging. **In the hosted deployment this is a hard requirement, not a default:** `--log-notes` is forced off and cannot be enabled, per `docs/DEPLOY_SPEC.md` DEPLOY-24, because the deployed surface is internet-reachable rather than a machine only the rater touches.

## Static serving

**Historical note, not a Deprecated clause:** from v1.0.0 through v1.1.0 this section read "`GET /` serves `web/index.html`, a two-card chooser linking to the conversation and clip pages." That file has never existed on disk at any point in this repository's history; `web/` has only ever held `clips.html`, `conversation.html`, and `README.md`. This was a spec defect, not a requirement later superseded by a real architectural change, so it is recorded here rather than wrapped in a `Deprecated` block — a `Deprecated` block would misrepresent it as having once been true and working. See `.claude/team-runs/2026-07-27-wave3a-specs/team_findings.md` for the discovery.

Current behavior, both modes, now that the SPA (`docs/WEB_SPEC.md`) supersedes the plan to migrate the two HTML files in place (see "Why keep the HTML at all" above):

- **Hosted:** Firebase Hosting serves the built SPA from its own static hosting, not from this bridge. The FastAPI app serves no static assets at all in the hosted configuration — it is API-only, reachable exclusively under `/api/**` through the Firebase Hosting rewrite (see `docs/DEPLOY_SPEC.md`'s Firebase Hosting clauses, Wave 3a).
- **Local `s2s serve`:** also API-only, and always has been correctly so once the non-existent `web/index.html` claim above is set aside — `s2s serve` binds `127.0.0.1:8787` and serves only the five endpoints in this document, nothing at `GET /` itself. What a rater runs locally to get a page in a browser is the SPA's own local dev server (`vite dev`) or a local preview of a production build, pointed at this bridge as its API origin; `docs/WEB_SPEC.md` is normative for how the SPA discovers that origin (an environment variable, never a hardcoded URL). This bridge's job stops at serving the API.

## Parity requirement

`tests/test_parity.py` asserts that for every golden fixture, `POST /evaluate` returns a verdict, finding-code set, and draft byte-identical to the CLI's `--json` output for the same input. The bridge is a transport, not a second implementation, and this test is what keeps it that way.
