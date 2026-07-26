# Artifact Registry repository for the bridge container image.
# docs/DEPLOY_SPEC.md DEPLOY-21: vulnerability scanning enabled, DEPLOY-22: images are
# deployed by digest, never by mutable tag.

resource "google_artifact_registry_repository" "s2s_harness" {
  project       = var.project_id
  location      = var.region
  repository_id = "s2s-harness"
  format        = "DOCKER"
  description   = "Bridge container images for s2s-harness. Deploys reference images by digest per docs/DEPLOY_SPEC.md DEPLOY-22."

  vulnerability_scanning_config {
    enablement_config = "INHERITED"
  }

  depends_on = [google_project_service.artifactregistry]
}
