# External HTTPS load balancer in front of the Cloud Run service, plus Cloud Armor.
# docs/DEPLOY_SPEC.md DEPLOY-5 (LB + managed cert + serverless NEG), DEPLOY-6 (ingress
# restricted to traverse the LB), DEPLOY-7/DEPLOY-8 (Cloud Armor as defense in depth,
# not a substitute for the API key check implemented in src/s2s_harness/bridge/auth.py).

resource "google_compute_region_network_endpoint_group" "bridge" {
  project               = var.project_id
  name                  = "${local.service_name}-neg"
  region                = var.region
  network_endpoint_type = "SERVERLESS"

  cloud_run {
    service = google_cloud_run_v2_service.bridge.name
  }
}

resource "google_compute_security_policy" "bridge" {
  project     = var.project_id
  name        = "${local.service_name}-armor"
  description = "Rate limiting and optional IP allowlist in front of the bridge. Identity is checked separately by the app-level API key. docs/DEPLOY_SPEC.md DEPLOY-7, DEPLOY-8."

  # Default rule: rate-limit everything not otherwise matched, rather than outright
  # deny, so a single noisy client is throttled instead of the service going dark for
  # everyone behind a shared NAT.
  rule {
    action   = "rate_based_ban"
    priority = 2147483647
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default rate limit for all traffic."
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"

      rate_limit_threshold {
        count        = var.rate_limit_threshold_count
        interval_sec = var.rate_limit_threshold_interval_sec
      }

      ban_duration_sec = 600
      ban_threshold {
        count        = var.rate_limit_threshold_count * 2
        interval_sec = var.rate_limit_threshold_interval_sec
      }
    }
  }

  # Optional IP allowlist, only materialized when the operator supplies ranges.
  # Defaulted off per docs/DEPLOY_SPEC.md DEPLOY-7 ("defaulted off but wired so the
  # operator can turn it on without a redeploy").
  dynamic "rule" {
    for_each = length(var.cloud_armor_ip_allowlist) > 0 ? [1] : []
    content {
      action   = "deny(403)"
      priority = 1000
      match {
        versioned_expr = "SRC_IPS_V1"
        config {
          src_ip_ranges = ["*"]
        }
      }
      description = "Deny everything not in the allowlist."
    }
  }

  dynamic "rule" {
    for_each = length(var.cloud_armor_ip_allowlist) > 0 ? [1] : []
    content {
      action   = "allow"
      priority = 900
      match {
        versioned_expr = "SRC_IPS_V1"
        config {
          src_ip_ranges = var.cloud_armor_ip_allowlist
        }
      }
      description = "Allow the operator-supplied IP allowlist."
    }
  }

  depends_on = [google_project_service.compute]
}

resource "google_compute_backend_service" "bridge" {
  project               = var.project_id
  name                  = "${local.service_name}-backend"
  protocol              = "HTTPS"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  security_policy       = google_compute_security_policy.bridge.id

  backend {
    group = google_compute_region_network_endpoint_group.bridge.id
  }
}

resource "google_compute_url_map" "bridge" {
  project         = var.project_id
  name            = "${local.service_name}-urlmap"
  default_service = google_compute_backend_service.bridge.id
}

resource "google_compute_managed_ssl_certificate" "bridge" {
  project = var.project_id
  name    = "${local.service_name}-cert"

  managed {
    domains = [var.ssl_domain]
  }
}

resource "google_compute_target_https_proxy" "bridge" {
  project          = var.project_id
  name             = "${local.service_name}-https-proxy"
  url_map          = google_compute_url_map.bridge.id
  ssl_certificates = [google_compute_managed_ssl_certificate.bridge.id]
}

resource "google_compute_global_address" "bridge" {
  project      = var.project_id
  name         = "${local.service_name}-ip"
  address_type = "EXTERNAL"
}

resource "google_compute_global_forwarding_rule" "bridge_https" {
  project               = var.project_id
  name                  = "${local.service_name}-fr-https"
  target                = google_compute_target_https_proxy.bridge.id
  port_range            = "443"
  ip_address            = google_compute_global_address.bridge.id
  load_balancing_scheme = "EXTERNAL_MANAGED"
}
