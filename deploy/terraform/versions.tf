# Terraform and provider version pins for the s2s-harness Cloud Run deployment.
# See docs/DEPLOY_SPEC.md for the design this implements.

terraform {
  required_version = ">= 1.9.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.0"
    }
  }
}
