output "load_balancer_ip" {
  description = "Reserved external IP for the HTTPS load balancer. Point ssl_domain's DNS A record here."
  value       = google_compute_global_address.bridge.address
}

output "cloud_run_service_uri" {
  description = "Direct Cloud Run URI. Not directly reachable per DEPLOY-6 (ingress restricted to the LB); shown for diagnostics only."
  value       = google_cloud_run_v2_service.bridge.uri
}

output "runtime_service_account_email" {
  description = "Runtime identity attached to the Cloud Run service."
  value       = google_service_account.runtime.email
}

output "deployer_service_account_email" {
  description = "CI deploy identity assumed via Workload Identity Federation."
  value       = google_service_account.deployer.email
}

output "workload_identity_provider" {
  description = "Full resource name of the WIF provider, for the google-github-actions/auth action's workload_identity_provider input."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository path for the bridge image, without tag or digest."
  value       = local.image_repository
}
