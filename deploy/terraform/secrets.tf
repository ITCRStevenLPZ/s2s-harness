# Secret Manager containers for the three deployment secrets.
# docs/DEPLOY_SPEC.md DEPLOY-16: s2s-app-api-key, anthropic-api-key, gemini-api-key,
# injected as Cloud Run secret references, never baked into the image or passed as a
# plain env var.
#
# Terraform manages the secret *containers* only. Secret *values* are never committed
# to this repository or passed as Terraform variables (which would land them in state).
# Populate versions out of band, e.g.:
#   printf '%s' "$KEY" | gcloud secrets versions add s2s-app-api-key --data-file=- --project="$PROJECT_ID"

resource "google_secret_manager_secret" "app_api_key" {
  project   = var.project_id
  secret_id = "s2s-app-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret" "anthropic_api_key" {
  project   = var.project_id
  secret_id = "anthropic-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret" "gemini_api_key" {
  project   = var.project_id
  secret_id = "gemini-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}
