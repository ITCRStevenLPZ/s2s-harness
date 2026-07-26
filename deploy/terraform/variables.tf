# Variable definitions for the s2s-harness Cloud Run deployment.
# See docs/DEPLOY_SPEC.md for the normative requirement each variable backs (DEPLOY-n).

variable "project_id" {
  description = "GCP project ID for this deployment. Deliberately left with no default: the user is creating a new dedicated project and has not named it. Must be set explicitly via terraform.tfvars or -var."
  type        = string
}

variable "region" {
  description = "Region for Cloud Run, Artifact Registry, and the serverless NEG. See docs/DEPLOY_SPEC.md DEPLOY-1."
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Deployment environment label, used in resource names and labels."
  type        = string
  default     = "prod"
}

variable "min_instance_count" {
  description = "Cloud Run minimum instance count. 0 means scale-to-zero. See docs/DEPLOY_SPEC.md DEPLOY-2."
  type        = number
  default     = 0
}

variable "max_instance_count" {
  description = "Cloud Run maximum instance count. Bounds cost and abuse blast radius, not a capacity plan. See docs/DEPLOY_SPEC.md DEPLOY-3."
  type        = number
  default     = 2
}

variable "container_cpu" {
  description = "CPU limit for the bridge container, as accepted by Cloud Run (e.g. \"1\")."
  type        = string
  default     = "1"
}

variable "container_memory" {
  description = "Memory limit for the bridge container, as accepted by Cloud Run (e.g. \"512Mi\")."
  type        = string
  default     = "512Mi"
}

variable "container_port" {
  description = "Port the bridge container listens on inside the container. Matches the Dockerfile's EXPOSE and PORT default."
  type        = number
  default     = 8787
}

variable "image_repository" {
  description = "Artifact Registry image path without tag or digest, e.g. \"us-central1-docker.pkg.dev/<project>/s2s-harness/bridge\". Composed from other variables at call site if left null."
  type        = string
  default     = null
}

variable "image_digest" {
  description = "Immutable image digest to deploy, in the form \"sha256:...\" (without the repository path). Required at apply time; deliberately has no default so a digest must be supplied explicitly per docs/DEPLOY_SPEC.md DEPLOY-22. A placeholder is used only to let `terraform validate` succeed before any real image has been pushed."
  type        = string
  default     = "sha256:0000000000000000000000000000000000000000000000000000000000000000"
}

variable "enable_gcp_stt" {
  description = "Whether S2S_STT_PROVIDER=gcp is enabled for this deployment. Gates the roles/speech.client grant per docs/DEPLOY_SPEC.md DEPLOY-20."
  type        = bool
  default     = false
}

variable "cloud_armor_ip_allowlist" {
  description = "Optional list of CIDR ranges to allow through Cloud Armor. Empty list means no IP allowlist rule is added (rate limiting alone still applies). See docs/DEPLOY_SPEC.md DEPLOY-7."
  type        = list(string)
  default     = []
}

variable "rate_limit_threshold_count" {
  description = "Cloud Armor rate limit: max requests allowed per client IP within rate_limit_threshold_interval_sec before the exceed action applies."
  type        = number
  default     = 100
}

variable "rate_limit_threshold_interval_sec" {
  description = "Cloud Armor rate limit window, in seconds."
  type        = number
  default     = 60
}

variable "ssl_domain" {
  description = "Public DNS name the Google-managed SSL certificate is issued for. Required at apply time; a placeholder default lets validate succeed without a real domain."
  type        = string
  default     = "s2s-harness.example.invalid"
}

variable "github_repository_owner" {
  description = "GitHub org or user that owns the repository allowed to assume the deploy service account via Workload Identity Federation. Required at apply time; see docs/DEPLOY_SPEC.md DEPLOY-23."
  type        = string
  default     = "CHANGE_ME_github_owner"
}

variable "github_repository" {
  description = "Full \"owner/repo\" GitHub repository allowed to assume the deploy service account via WIF."
  type        = string
  default     = "CHANGE_ME_github_owner/s2s-harness"
}
