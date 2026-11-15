output "cloud_run_service_name" {
  value = google_cloud_run_v2_service.primary.name
}
output "cloud_run_uri" {
  value = google_cloud_run_v2_service.primary.uri
}

output "load_balancer_ipv4" {
  value = google_compute_global_address.primary.address
}

output "certificate_dns_authorization_record" {
  value = google_certificate_manager_dns_authorization.primary.dns_resource_record
}
