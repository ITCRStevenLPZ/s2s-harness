# Service accounts and least-privilege IAM grants.
# docs/DEPLOY_SPEC.md DEPLOY-19: dedicated runtime SA, no default compute SA, no
# project-level Owner/Editor. DEPLOY-20: per-secret accessor grants, speech.client only
# when GCP STT is enabled.

resource "google_service_account" "runtime" {
  project      = var.project_id
  account_id   = "s2s-runtime"
  display_name = "s2s-harness Cloud Run runtime identity"
  description  = "Attached to the Cloud Run service. Supplies Application Default Credentials in place of a GOOGLE_APPLICATION_CREDENTIALS JSON key file (docs/DEPLOY_SPEC.md DEPLOY-17)."

  depends_on = [google_project_service.iam]
}

resource "google_service_account" "deployer" {
  project      = var.project_id
  account_id   = "s2s-deployer"
  display_name = "s2s-harness CI deploy identity"
  description  = "Assumed by GitHub Actions via Workload Identity Federation to build, push, and deploy. No long-lived key. See docs/DEPLOY_SPEC.md DEPLOY-23."

  depends_on = [google_project_service.iam]
}

# Per-secret accessor grants for the runtime SA, one resource per secret so access is
# bound to the individual secret rather than granted project-wide.
resource "google_secret_manager_secret_iam_member" "runtime_app_api_key" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.app_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_secret_manager_secret_iam_member" "runtime_anthropic_api_key" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.anthropic_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_secret_manager_secret_iam_member" "runtime_gemini_api_key" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.gemini_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

# Only granted when GCP Speech-to-Text is the configured provider. Gemini-only
# deployments have no need for this role. See docs/DEPLOY_SPEC.md DEPLOY-18, DEPLOY-20.
resource "google_project_iam_member" "runtime_speech_client" {
  count   = var.enable_gcp_stt ? 1 : 0
  project = var.project_id
  role    = "roles/speech.client"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

# CI deploy identity: push images and deploy revisions. Scoped to Artifact Registry
# write and Cloud Run deploy, never project Editor/Owner.
resource "google_project_iam_member" "deployer_artifact_registry_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_project_iam_member" "deployer_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

# The deployer must be able to act as the runtime SA when deploying a revision that
# attaches it (Cloud Run requires iam.serviceAccounts.actAs on the runtime identity).
resource "google_service_account_iam_member" "deployer_act_as_runtime" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deployer.email}"
}
