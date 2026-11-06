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
variable "service_account_id" {
  type    = string
  default = "mcdr-primary-api"
}
