# Deployment specification

Version: 1.0.0
Last updated: 2026-07-26

ID convention: `**DEPLOY-n.**` leading tag at the start of each normative paragraph, sequential in document order, gaps allowed for later insertions. This differs in placement from T1's trailing `{RULE-n}`-style tags used in the engine-facing specs; confirmed with T1 via the durable record (`team_findings.md`, "[T1 -> T5-gcp-deploy] ID convention reply") that this is fine as-is: `DEPLOY-n` and T1's six prefixes are disjoint namespaces in disjoint files, so visual placement does not need to match across the two halves of `docs/`. What matters and does match: the `Version` / `Last updated` header block directly under the H1.

This spec governs the hosted deployment of the bridge (`docs/BRIDGE_SPEC.md`) on GCP Cloud Run. It exists because the user has decided to host the harness remotely, which directly contradicts the loopback-only, no-auth posture that `BRIDGE_SPEC.md` and `ARCHITECTURE.md` originally specified for a single rater on a local machine. Those clauses are not deleted — they are marked `Deprecated` in place in their home documents, pointing here. Loopback-only remains correct and binding for `s2s serve` run locally; nothing in this document changes that path. Everything in this document applies only when the bridge runs as a Cloud Run service.

No infrastructure described here has been applied. This is the design; `deploy/terraform/` is the implementation, validated but never `apply`d by this wave.

---

## 1. Deployment target

**DEPLOY-1.** The bridge deploys as a single stateless container to Cloud Run.

The bridge (`docs/BRIDGE_SPEC.md`) is a single-process FastAPI app with no persistent state of its own — `EvaluationState` lives in the request/response cycle, and the only durable artifact is the content-addressed polish cache under `.s2s-cache/`, which is a local performance optimization, not a correctness dependency (`docs/ARCHITECTURE.md`, Draft-hash caching). Each `/evaluate` call is a complete run: nothing needs to survive past the response. That makes Cloud Run's request-scoped, horizontally-scaled model a fit without any redesign of the engine.

**DEPLOY-2.** `min-instances = 0` (scale to zero). There is exactly one rater. Paying to keep a container warm for a service with no continuous traffic is waste, and scale-to-zero has no correctness cost here because the app holds no in-memory state across requests that matters once a run completes.

**DEPLOY-3.** `max-instances` is capped (default 2, a Terraform variable) to bound both cost and the blast radius of any abuse that gets past Cloud Armor and the API key check. This is not a capacity plan — a single rater does not need concurrency — it is a ceiling.

**DEPLOY-4.** No database, no attached persistent volume, no session store. See §8.

---

## 2. Network posture

**DEPLOY-5.** Public entry is an external HTTPS Application Load Balancer with a Google-managed TLS certificate, fronting a serverless NEG that targets the Cloud Run service.

**DEPLOY-6.** The Cloud Run service's ingress setting is `internal-and-cloud-load-balancing` (the `gcloud`/API surface name; the Terraform/REST enum for the same setting is `INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER`, used in `deploy/terraform/cloud_run.tf`). The service is never directly reachable at its default `*.run.app` URL; every request must traverse the load balancer.

**DEPLOY-7.** A Cloud Armor security policy is attached to the load balancer's backend service, providing rate limiting (per-IP request throttling) and an optional IP allowlist, defaulted off but wired so the operator can turn it on without a redeploy.

**DEPLOY-8.** This is deliberate defense in depth, not redundancy. The app-level API key (§3) is the identity check — it answers "is this caller authorized." Cloud Armor is the volumetric and origin control — it answers "is this traffic pattern abusive, regardless of whether the key is valid." A leaked key without Cloud Armor still lets an attacker hammer the service; Cloud Armor without a key lets anyone who reaches the LB in. Neither substitutes for the other.

---

## 3. Authentication

The deployed bridge requires an app-level API key. `docs/BRIDGE_SPEC.md`'s original "no auth, loopback-only" posture is superseded for this deployment mode only (see the Deprecated markers in that file). This section is the normative source for auth behavior; implemented at `BUILD_PLAN.md` Phase 7.

**DEPLOY-9.** Location: `src/s2s_harness/bridge/auth.py`. Implemented as a FastAPI dependency (or `Depends`-injected middleware) applied to every route except the one exempted in DEPLOY-13.

**DEPLOY-10.** Header: `X-S2S-Key`. The client sends the shared secret in this header on every request.

**DEPLOY-11.** Comparison: `hmac.compare_digest(provided, expected)`. Never `==` and never a `startswith`/substring check. A naive equality comparison on a secret short-circuits on the first mismatched byte, which leaks timing information proportional to how many leading bytes are correct — a real, exploitable side channel against a shared secret, not a theoretical one. `hmac.compare_digest` runs in constant time regardless of where the mismatch occurs.

**DEPLOY-12.** The key itself is never hardcoded, never checked into `deploy/`, and is read from the environment at startup (populated from Secret Manager per §4). Missing key at startup is a hard failure — see DEPLOY-14.

**DEPLOY-13.** `GET /health` is exempt from the key check. The load balancer's health check and the front end's availability badge (`docs/BRIDGE_SPEC.md` `GET /health`) both need to reach it unauthenticated, and an LB health check cannot be taught a secret header without becoming another secret to manage. Its response body — `{"ok": true, "stt": "gemini", "llm": true, "version": "<semver>"}` (`version` read via `importlib.metadata.version("s2s-harness")` per `VERSIONING.md`, confirmed with `ci-dev`) — is explicitly reviewed here and judged safe to expose without auth: it names which STT provider class is configured (not credentials), whether the polish path is enabled (a boolean, not a key), and the running semver. None of that is a secret, a capability grant, or information that materially assists an attacker beyond what "this is an S2S harness bridge" already reveals from the response shape itself.

**DEPLOY-14.** Every other endpoint returns `401` when the header is absent or the key does not match. There is no "allow if unset" fallback. A missing `S2S_APP_API_KEY` (or equivalent) in the environment is a startup error, not a silent open door — this mirrors `docs/STT_SPEC.md` §8's rule for a missing STT credential ("Never silently degrade"). The same discipline applies to the auth boundary: an unconfigured key must fail loud at boot, not fail open at request time.

**DEPLOY-15.** `src/s2s_harness/bridge/auth.py` must not import from `src/s2s_harness/rules/`. Authentication is a transport concern; the rules layer stays pure per `docs/ARCHITECTURE.md`'s layer-boundary table (`rules/` may not be imported by `cli/`, `bridge/` directly — go through the graph). This keeps the token-boundary AST test (`tests/test_layering.py`) passing without a carve-out.

---

## 4. Secrets

**DEPLOY-16.** Secret Manager holds three secrets: `s2s-app-api-key`, `anthropic-api-key`, `gemini-api-key`. Each is injected into the Cloud Run service as a secret environment variable reference (`--set-secrets` / the Terraform `google_cloud_run_v2_service` `env` block with `value_source.secret_key_ref`), never baked into the container image and never passed as a plain Terraform `env` string.

**DEPLOY-17.** `GOOGLE_APPLICATION_CREDENTIALS` (the service-account JSON file path documented in `.env.example` for local use) is dropped entirely in the deployed configuration. The Cloud Run runtime service account (§5) supplies Application Default Credentials automatically via the attached identity; there is no JSON key file to mount, rotate, or leak. This removes an entire secret and an entire file-mount from the threat model compared to the local-dev path — it is a strict improvement, not a parity gap. `.env.example` continues to document `GOOGLE_APPLICATION_CREDENTIALS` for local use only; that file is T4-owned and any deployment note there is theirs to add.

**DEPLOY-18.** `S2S_STT_PROVIDER=gcp` deployments therefore authenticate purely via the runtime SA's ADC. `S2S_STT_PROVIDER=gemini` deployments still need `gemini-api-key` from Secret Manager, since Gemini API access is a bearer key, not an IAM-federated identity.

---

## 5. IAM

**DEPLOY-19.** A dedicated Cloud Run runtime service account (`s2s-runtime@<project>.iam.gserviceaccount.com`) is created and attached to the service. The default compute service account is never used, and no role is granted at the project-Owner/Editor level.

**DEPLOY-20.** Grants, least privilege:

| Role | Scope | Condition |
|---|---|---|
| `roles/secretmanager.secretAccessor` | Per-secret, on each of the three individual secret resources | Always |
| `roles/speech.client` | Project | Only if `S2S_STT_PROVIDER=gcp` is enabled for the deployment |

No `roles/editor`, no `roles/owner`, no broad `roles/secretmanager.admin`. Secret access is bound to the specific secret resource, not granted project-wide, so compromising the runtime SA does not expose secrets this deployment does not use.

---

## 6. Supply chain

**DEPLOY-21.** Container images are stored in Artifact Registry with vulnerability scanning enabled on the repository.

**DEPLOY-22.** Deploys reference the image by immutable digest (`@sha256:...`), never by a mutable tag such as `:latest` or `:main`. A tag can be repointed after the fact; a digest cannot. This is what makes "what is actually running" a verifiable question instead of a trust claim. `release.yml` pushes two tags on every release, `<registry-path>:X.Y.Z` and `<registry-path>:<full-commit-sha>`, both pointing at the same digest — tag format itself is fixed in `VERSIONING.md` (owned by `ci-dev`), not duplicated here; this clause is about what Cloud Run deploys from, which is the digest, never either tag.

**DEPLOY-23.** CI authenticates to GCP via Workload Identity Federation for GitHub Actions OIDC. No long-lived service-account JSON key exists anywhere — not in GitHub Actions secrets, not on disk, not in this repo. Confirmed in writing with `ci-dev` (`team_findings.md`, "[T5 <-> T4-ci-dev] WIF and registry naming confirmed"):

- WIF pool: `github-pool`. Provider: `github-provider`. Full provider resource name for the `google-github-actions/auth` action's `workload_identity_provider` input: `projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/github-pool/providers/github-provider` (project *number*, not project ID; read from `terraform output workload_identity_provider` after apply).
- Deploy service account release.yml assumes: `s2s-deployer@<project-id>.iam.gserviceaccount.com`.
- Registry path: `<region>-docker.pkg.dev/<project-id>/s2s-harness/bridge` (region defaults to `us-central1`, both variables in `deploy/terraform/variables.tf`).
- `deploy/terraform/wif.tf` and `artifact_registry.tf` implement this naming.

---

## 7. Privacy

**DEPLOY-24.** `docs/BRIDGE_SPEC.md`'s "no request logging of note content by default; `--log-notes` opts in for debugging" clause holds by default everywhere, but in the deployed configuration `--log-notes` is forced off unconditionally — the deploy entrypoint does not expose a way to turn it on. Rater note content (the substance of what they observed about the models under test) must never reach Cloud Logging or any GCP-managed log sink. This is a hard requirement, not a default that an operator flag can override, because the deployed surface is reachable over the internet (behind the LB and API key) rather than a machine only the rater can touch.

**DEPLOY-25.** A log-based metric and alert on repeated `401` responses (auth failures) from the same source is recommended, so a credential-guessing pattern is visible to the operator instead of silently absorbed by the rate limiter.

---

## 8. What is still deliberately absent

**DEPLOY-26.** No database. No multi-user support — the deployed bridge still serves exactly one rater's workflow, just reachable over HTTPS instead of `127.0.0.1`. No server-side session state; each `/evaluate` and `/polish` call is self-contained per `docs/BRIDGE_SPEC.md`. No clip audio is ever sent to any provider in the deployed configuration either — `docs/STT_SPEC.md` §6 ("No provider ever receives a model clip in the default path") is a rule about what the STT layer does with audio, and hosting the bridge on Cloud Run does not touch that layer's behavior at all. It remains fully binding.

---

## Traceability

This spec supersedes, for the hosted-deployment case only, the following clauses: `docs/BRIDGE_SPEC.md` "Bind `127.0.0.1` only" and "No auth" (superseded by DEPLOY-6 and DEPLOY-9 through DEPLOY-15 respectively), and `docs/ARCHITECTURE.md` "No auth, no multi-user" (superseded by DEPLOY-9 through DEPLOY-15; multi-user remains correctly absent per DEPLOY-26). Both source documents mark their superseded clauses `Deprecated` in place with a pointer back here, per the CLAUDE.md deprecation rule. Neither clause is deleted.
