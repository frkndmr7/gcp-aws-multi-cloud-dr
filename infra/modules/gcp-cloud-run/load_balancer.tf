resource "google_project_service" "certificate_manager" {
  project            = var.project_id
  service            = "certificatemanager.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "compute" {
  project            = var.project_id
  service            = "compute.googleapis.com"
  disable_on_destroy = false
}

resource "google_compute_global_address" "primary" {
  project      = var.project_id
  name         = "mcdr-primary-lb-ip"
  address_type = "EXTERNAL"
  ip_version   = "IPV4"
  depends_on   = [google_project_service.compute]
}

resource "google_compute_region_network_endpoint_group" "cloud_run" {
  project               = var.project_id
  name                  = "mcdr-primary-serverless-neg"
  region                = var.region
  network_endpoint_type = "SERVERLESS"
  cloud_run {
    service = google_cloud_run_v2_service.primary.name
  }
  depends_on = [google_project_service.compute]
}

resource "google_compute_backend_service" "primary" {
  project               = var.project_id
  name                  = "mcdr-primary-backend"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  protocol              = "HTTP"
  backend {
    group = google_compute_region_network_endpoint_group.cloud_run.id
  }
}

resource "google_compute_url_map" "primary" {
  project         = var.project_id
  name            = "mcdr-primary-url-map"
  default_service = google_compute_backend_service.primary.id
}

resource "google_compute_target_https_proxy" "primary" {
  project         = var.project_id
  name            = "mcdr-primary-https-proxy"
  url_map         = google_compute_url_map.primary.id
  certificate_map = "//certificatemanager.googleapis.com/${google_certificate_manager_certificate_map.primary.id}"
  depends_on      = [google_certificate_manager_certificate_map_entry.primary]
}

resource "google_compute_global_forwarding_rule" "https" {
  project               = var.project_id
  name                  = "mcdr-primary-https"
  ip_address            = google_compute_global_address.primary.id
  ip_protocol           = "TCP"
  port_range            = "443"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  target                = google_compute_target_https_proxy.primary.id
}
