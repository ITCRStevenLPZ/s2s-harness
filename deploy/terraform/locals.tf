locals {
  image_repository = coalesce(
    var.image_repository,
    "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.s2s_harness.repository_id}/bridge",
  )

  # Deployed strictly by digest, never by mutable tag. See docs/DEPLOY_SPEC.md DEPLOY-22.
  image = "${local.image_repository}@${var.image_digest}"

  service_name = "s2s-harness-bridge"
}
