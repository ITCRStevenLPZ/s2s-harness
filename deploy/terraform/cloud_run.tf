# The bridge as a Cloud Run v2 service.
# docs/DEPLOY_SPEC.md DEPLOY-1..DEPLOY-4 (target), DEPLOY-6 (ingress), DEPLOY-16..18
# (secrets), DEPLOY-19..20 (IAM), DEPLOY-24 (log-notes forced off).

resource "google_cloud_run_v2_service" "bridge" {
  project  = var.project_id
  name     = local.service_name
  location = var.region

  # Never directly reachable at the default run.app URL; every request must traverse
  # the load balancer in front of the serverless NEG. docs/DEPLOY_SPEC.md DEPLOY-6.
  # Terraform/API enum for the gcloud --ingress=internal-and-cloud-load-balancing value.
  ingress = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  deletion_protection = false

  template {
    service_account = google_service_account.runtime.email

    # gen2 required for some networking features and matches the read-only-root-fs
    # posture documented in the Dockerfile; gen1 is the alternative if a future
    # dependency needs it.
    execution_environment = "EXECUTION_ENVIRONMENT_GEN2"

    scaling {
      min_instance_count = var.min_instance_count
      max_instance_count = var.max_instance_count
    }

    containers {
      image = local.image

      ports {
        container_port = var.container_port
      }

      resources {
        limits = {
          cpu    = var.container_cpu
          memory = var.container_memory
        }
      }

      env {
        name  = "PORT"
        value = tostring(var.container_port)
      }

      env {
        name  = "S2S_STT_PROVIDER"
        value = var.enable_gcp_stt ? "gcp" : "gemini"
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }

      # Forced off in the deployed configuration: rater note content must never reach
      # Cloud Logging. docs/DEPLOY_SPEC.md DEPLOY-24. Not an operator-settable default
      # here; the bridge implementation must treat this deployment's absence of a
      # --log-notes flag as authoritative, not merely as an unset default.
      env {
        name  = "S2S_LOG_NOTES"
        value = "0"
      }

      # GOOGLE_APPLICATION_CREDENTIALS is deliberately absent: the runtime service
      # account supplies Application Default Credentials. docs/DEPLOY_SPEC.md DEPLOY-17.

      env {
        name = "S2S_APP_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.app_api_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "ANTHROPIC_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.anthropic_api_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_api_key.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [
    google_project_service.run,
    google_secret_manager_secret_iam_member.runtime_app_api_key,
    google_secret_manager_secret_iam_member.runtime_anthropic_api_key,
    google_secret_manager_secret_iam_member.runtime_gemini_api_key,
  ]

  lifecycle {
    # The image is deployed by digest from CI (docs/DEPLOY_SPEC.md DEPLOY-22, DEPLOY-23).
    # Terraform still declares the field so `plan`/`validate` see a complete resource;
    # ignore drift from CI-driven redeploys between Terraform runs.
    ignore_changes = [template[0].containers[0].image]
  }
}
