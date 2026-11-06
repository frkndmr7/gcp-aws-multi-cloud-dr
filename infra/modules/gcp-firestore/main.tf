resource "google_firestore_database" "primary" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.firestore_location
  type        = "FIRESTORE_NATIVE"

  lifecycle {
    prevent_destroy = true
  }
}
