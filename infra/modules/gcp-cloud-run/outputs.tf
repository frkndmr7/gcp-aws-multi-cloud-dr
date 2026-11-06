output "cloud_run_service_name" {
  value = google_cloud_run_v2_service.primary.name
}
output "cloud_run_uri" {
  value = google_cloud_run_v2_service.primary.uri
}
