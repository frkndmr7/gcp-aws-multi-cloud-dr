resource "google_certificate_manager_dns_authorization" "primary" {
  project    = var.project_id
  name       = "mcdr-primary-dns-auth"
  domain     = "app.shorturldr.online"
  type       = "PER_PROJECT_RECORD"
  depends_on = [google_project_service.certificate_manager]
}

resource "google_certificate_manager_certificate" "primary" {
  project = var.project_id
  name    = "mcdr-primary-cert"
  managed {
    domains            = ["app.shorturldr.online"]
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
  hostname     = "app.shorturldr.online"
  certificates = [google_certificate_manager_certificate.primary.id]
}
