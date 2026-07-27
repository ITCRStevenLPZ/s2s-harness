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

Every endpoint below except `GET /health` requires an `Authorization: Bearer <idToken>` header carrying a Firebase ID token in the hosted deployment; the server verifies it per `docs/DEPLOY_SPEC.md` DEPLOY-27 through DEPLOY-30 (signature/audience/issuer/expiry, the `@softical.tech` domain check on the verified `email` claim, and the `401` vs `403` split). `GET /health` stays exempt — see that endpoint's entry below and `docs/DEPLOY_SPEC.md` DEPLOY-13, which survives Wave 3a unchanged because its reasoning (a front door's health check and the front end's availability badge both need unauthenticated reach, and the response body is safe to expose) is auth-mechanism agnostic. Local `s2s serve` requires no header at all, per its unchanged unauthenticated posture below. This section does not redesign the five endpoint shapes themselves; `BUILD_PLAN.md` Phase 7 implements them as specified here.

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
`{"ok": true, "stt": "gemini", "llm": true, "version": "0.1.0"}` — lets the page show the same availability badge the artifacts show today. `version` is read at runtime via `importlib.metadata.version("s2s-harness")`, the same mechanism `s2s --version` uses (single source of truth: `[project] version` in `pyproject.toml`, see `VERSIONING.md`) — never a hardcoded copy. See `docs/DEPLOY_SPEC.md` DEPLOY-13 for why this endpoint stays unauthenticated in the hosted deployment (true under both the retired API key and the current Firebase ID-token check, DEPLOY-27) and why that response body, including `version`, is safe to expose without any credential.

## Security posture

- **Local `s2s serve` (default, unchanged):** Bind `127.0.0.1` only. Never `0.0.0.0`.
- **Deprecated (local-only scope; superseded for hosted deployment).** Originally: "Bind `127.0.0.1` only. Never `0.0.0.0`" applied unconditionally. It still applies to local `s2s serve` without qualification — nothing about local usage changed. For the hosted Cloud Run deployment, the container binds `0.0.0.0:$PORT` as Cloud Run requires. Whether it is "never directly reachable" at its `*.run.app` URL has changed, and the chain below is the whole history — follow it once, not as nested archaeology:
  1. **Wave 1:** ingress restricted to `internal-and-cloud-load-balancing` (the original `docs/DEPLOY_SPEC.md` DEPLOY-6), so every external request traversed an external HTTPS load balancer and the `run.app` URL was not directly reachable at all.
  2. **Wave 3a, current:** DEPLOY-6 is deprecated, superseded by `docs/DEPLOY_SPEC.md` **DEPLOY-32**: ingress is now `all`, not `internal-and-cloud-load-balancing`, because a Firebase Hosting rewrite (**DEPLOY-31**, superseding DEPLOY-5) invokes Cloud Run at its default `run.app` URL directly rather than through load-balancing infrastructure, and the old restricted ingress setting would block the rewrite's own traffic along with everything else. DEPLOY-32 documents the GCP-documentation citation for this; it is not re-derived here.

  **This is a real change in reachability, not a wording update, and BRIDGE_SPEC states the consequence plainly rather than letting it hide in a cross-reference:** the Cloud Run service is now directly reachable at its `run.app` URL over the public internet, bypassing Firebase Hosting entirely — a request never has to go through the Hosting rewrite to reach this bridge. It does **not** bypass authentication: token verification (DEPLOY-27) runs as a FastAPI dependency in application code, not as a network-layer control, so a direct `run.app` request hits the identical check and is rejected without a valid `@softical.tech` bearer token exactly as a request through Hosting would be. What is lost is DEPLOY-6's old guarantee that every request had already traversed a controlled front door before reaching application code at all; what remains is that application-layer auth is now the **first and only** line of defense for this endpoint set, not the last of three (compare `docs/DEPLOY_SPEC.md`'s amended DEPLOY-8 defense-in-depth discussion, which reaches the same conclusion from the network side). Do not describe this posture as equivalent to Wave 1's.
- **CORS.** This bullet has read "Hosted mode's CORS allowlist is the load balancer's public hostname; see `docs/DEPLOY_SPEC.md`" since v1.0.0. **That cross-reference has been dangling for the entire life of this document: `docs/DEPLOY_SPEC.md` has never contained a CORS clause.** Recorded here explicitly, not quietly patched, because an unnoticed dangling reference is exactly the kind of defect that recurs when the fix is silent instead of named (confirmed by re-reading all of DEPLOY-1 through DEPLOY-26 in Wave 3a; none mention CORS).

  The Hosting rewrite happens to make the dangling reference moot rather than requiring a real fix: Firebase Hosting rewrites `/api/**` to the Cloud Run service, so the browser loads the SPA and calls the API from the same origin (the Hosting domain). Same-origin requests are not subject to CORS at all — no preflight, no `Access-Control-*` response headers, no allowlist to maintain, in the hosted configuration. This restores, for the hosted case, the same-origin property this document's now-superseded "Static serving" section originally valued ("Serving them from the same origin as the API avoids CORS entirely") — the mechanism changed from "FastAPI serves the HTML" to "Hosting rewrites to FastAPI", but the same-origin property it produces is the same one, not a reopened cross-origin split.

  **Local mode still needs a real CORS allowlist, and this is the deliberate opposite of the hosted case above, not a smaller version of the same rule.** Local development is genuinely cross-origin now that the SPA replaces file:// HTML: the Vite dev server (`vite dev`, default `http://localhost:5173`) and a local production-build smoke test (`vite preview`, default `http://localhost:4173`) are both different origins than the bridge (`http://127.0.0.1:8787`), per `docs/WEB_SPEC.md` **WEB-4** (confirmed directly with T3). The local allowlist is therefore both `http://localhost:5173` and `http://localhost:4173`, replacing the old `null` (file://) entry now that file-opened HTML no longer exists. **State this asymmetry plainly so it is not "simplified" away later:** hosted mode has no CORS allowlist because the Hosting rewrite makes it same-origin; local mode has a two-entry CORS allowlist because dev/preview and the bridge are genuinely different origins. Neither environment's rule generalizes to the other — do not add a hosted-mode allowlist for symmetry, and do not drop the local one on the theory that "the hosted config doesn't need one."
- **Deprecated (local-only scope; superseded for hosted deployment).** Originally (v1.0.0): "No auth — the surface is loopback-only and single-user. Do not add remote deployment without revisiting this." Local `s2s serve` remains correctly unauthenticated — a loopback bind on a single-user machine has no one to authenticate against; nothing about that has ever changed. The hosted deployment's auth mechanism has itself been revisited once since. Recorded as one chain, not a Deprecated block nested inside a Deprecated block, so a reader follows one path instead of an archaeology dig:
  1. **Wave 1:** an app-level shared-secret API key — `X-S2S-Key` header, `hmac.compare_digest` comparison, `GET /health` exempt — specified in the original `docs/DEPLOY_SPEC.md` DEPLOY-9 through DEPLOY-15 (DEPLOY-9, 10, 11, 12, 14 are now deprecated in that document; DEPLOY-13 and DEPLOY-15 survive, see below).
  2. **Wave 3a, current:** the shared-secret mechanism is superseded by Firebase ID-token verification, `docs/DEPLOY_SPEC.md` **DEPLOY-27 through DEPLOY-30**: `Authorization: Bearer <idToken>` verified server-side (signature, audience, issuer, expiry — DEPLOY-27), the `@softical.tech` domain checked on the verified `email` claim with `email_verified` required true (DEPLOY-28, DEPLOY-30), and a `401`-vs-`403` split (DEPLOY-29) — `401` when the bridge cannot tell who is asking, `403` when it can and the account is not allowed. `GET /health` stays exempt from either mechanism, per **DEPLOY-13**, which survives unchanged because its reasoning was always auth-mechanism agnostic (a front door's health probe and the front end's availability badge both need unauthenticated reach, and the response body was already reviewed as safe to expose). The module boundary itself — `src/s2s_harness/bridge/auth.py`, must not import `rules/` — is **DEPLOY-15**, also unchanged.

  Do not treat the Wave 1 shared-secret mechanism as still live when reading this bullet — it is superseded, not one of two current options.
- No request logging of note content by default; `--log-notes` opts in for debugging. **In the hosted deployment this is a hard requirement, not a default:** `--log-notes` is forced off and cannot be enabled, per `docs/DEPLOY_SPEC.md` DEPLOY-24, because the deployed surface is internet-reachable rather than a machine only the rater touches.

## Static serving

**Historical note, not a Deprecated clause:** from v1.0.0 through v1.1.0 this section read "`GET /` serves `web/index.html`, a two-card chooser linking to the conversation and clip pages." That file has never existed on disk at any point in this repository's history; `web/` has only ever held `clips.html`, `conversation.html`, and `README.md`. This was a spec defect, not a requirement later superseded by a real architectural change, so it is recorded here rather than wrapped in a `Deprecated` block — a `Deprecated` block would misrepresent it as having once been true and working. See `.claude/team-runs/2026-07-27-wave3a-specs/team_findings.md` for the discovery.

Current behavior, both modes, now that the SPA (`docs/WEB_SPEC.md`) supersedes the plan to migrate the two HTML files in place (see "Why keep the HTML at all" above):

- **Hosted:** Firebase Hosting serves the built SPA from its own static hosting, not from this bridge. The FastAPI app serves no static assets at all in the hosted configuration — it is API-only, reachable exclusively under `/api/**` through the Firebase Hosting rewrite (`docs/DEPLOY_SPEC.md` DEPLOY-31).
- **Local `s2s serve`:** also API-only, and always has been correctly so once the non-existent `web/index.html` claim above is set aside — `s2s serve` binds `127.0.0.1:8787` and serves only the five endpoints in this document, nothing at `GET /` itself. What a rater runs locally to get a page in a browser is the SPA's own local dev server (`vite dev`) or a local preview of a production build, pointed at this bridge as its API origin; `docs/WEB_SPEC.md` is normative for how the SPA discovers that origin (an environment variable, never a hardcoded URL). This bridge's job stops at serving the API.

## Parity requirement

`tests/test_parity.py` asserts that for every golden fixture, `POST /evaluate` returns a verdict, finding-code set, and draft byte-identical to the CLI's `--json` output for the same input. The bridge is a transport, not a second implementation, and this test is what keeps it that way.
