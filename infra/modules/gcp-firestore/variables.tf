variable "project_id" {
  type = string
  validation {
    condition     = length(trimspace(var.project_id)) > 0
    error_message = "A GCP project ID is required."
  }
}
variable "region" {
  type = string
  validation {
    condition     = length(trimspace(var.region)) > 0
    error_message = "A Cloud Run region is required."
  }
}
variable "firestore_location" {
  type = string
  validation {
    condition     = length(trimspace(var.firestore_location)) > 0
    error_message = "A Firestore location is required and cannot be changed after creation."
  }
}
