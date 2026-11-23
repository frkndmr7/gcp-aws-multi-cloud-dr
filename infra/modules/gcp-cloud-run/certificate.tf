resource "google_certificate_manager_dns_authorization" "primary" {
  project    = var.project_id
  name       = "mcdr-primary-dns-auth"
  domain     = var.domain_name
  type       = "PER_PROJECT_RECORD"
  depends_on = [google_project_service.certificate_manager]
}

resource "google_certificate_manager_certificate" "primary" {
  project = var.project_id
  name    = "mcdr-primary-cert"
  managed {
    domains            = [var.domain_name]
    dns_authorizations = [google_certificate_manager_dns_authorization.primary.id]
  }
}

resource "google_certificate_manager_certificate_map" "primary" {
  project    = var.project_id
  name       = "mcdr-primary-cert-map"
  depends_on = [google_project_service.certificate_manager]
}

resource "google_certificate_manager_certificate_map_entry" "primary" {
  project      = var.project_id
  name         = "mcdr-primary-cert-entry"
  map          = google_certificate_manager_certificate_map.primary.name
  hostname     = var.domain_name
  certificates = [google_certificate_manager_certificate.primary.id]
}
