# Workload Identity Federation for GitHub Actions OIDC, so CI never holds a long-lived
# service-account JSON key. docs/DEPLOY_SPEC.md DEPLOY-23. Naming agreed with T4-ci-dev
# (owns .github/workflows/release.yml) via SendMessage; see team_findings.md for
# confirmation once received.

resource "google_iam_workload_identity_pool" "github" {
  project                   = var.project_id
  workload_identity_pool_id = "github-pool"
  display_name              = "GitHub Actions"
  description               = "Pool for GitHub Actions OIDC federation, s2s-harness CI/CD."

  depends_on = [google_project_service.iam, google_project_service.sts]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub Actions OIDC"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.owner"      = "assertion.repository_owner"
    "attribute.ref"        = "assertion.ref"
  }

  # Restrict to this repository only, per docs/DEPLOY_SPEC.md DEPLOY-23. Narrower than
  # gating on repository_owner alone, so a same-org sibling repo cannot assume this
  # identity.
  attribute_condition = "assertion.repository == \"${var.github_repository}\""

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# Binds the deployer SA so only workflow runs from the named GitHub repository can
# impersonate it, scoped further by attribute_condition above.
resource "google_service_account_iam_member" "deployer_wif_binding" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}
