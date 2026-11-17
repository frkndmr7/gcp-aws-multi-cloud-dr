resource "google_project_iam_member" "eventarc_service_agent" {
  project = var.project_id
  role    = "roles/eventarc.serviceAgent"
  member  = "serviceAccount:service-900932589626@gcp-sa-eventarc.iam.gserviceaccount.com"
}
