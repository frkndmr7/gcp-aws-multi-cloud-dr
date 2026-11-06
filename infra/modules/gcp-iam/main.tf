resource "google_project_service" "required" {
  for_each = toset(["run.googleapis.com", "firestore.googleapis.com", "iam.googleapis.com"])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_service_account" "run" {
  project      = var.project_id
  account_id   = var.service_account_id
  display_name = "Multi-cloud DR primary application"
  depends_on   = [google_project_service.required]
}

resource "google_project_iam_member" "firestore_access" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.run.email}"
}
