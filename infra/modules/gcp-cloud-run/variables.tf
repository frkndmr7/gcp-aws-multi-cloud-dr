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
variable "image" {
  type = string
  validation {
    condition     = can(regex("@sha256:[a-f0-9]{64}$", var.image))
    error_message = "Supply an existing image pinned to a SHA-256 digest."
  }
}
variable "service_name" {
  type    = string
  default = "mcdr-primary-api"
}
variable "cpu" {
  type    = string
  default = "1"
}
variable "memory" {
  type    = string
  default = "512Mi"
}
variable "max_instances" {
  type    = number
  default = 1
}
variable "environment" {
  description = "Non-secret application environment variables."
  type        = map(string)
  default = {
    SERVING_PROVIDER = "gcp"
    CLOUD_ROLE       = "primary"
    WRITER_MODE      = "frozen"
    DR_READY         = "false"
  }
  validation {
    condition     = lookup(var.environment, "SERVING_PROVIDER", "") == "gcp" && lookup(var.environment, "WRITER_MODE", "") == "frozen" && lookup(var.environment, "DR_READY", "") == "false"
    error_message = "Initial core deployment must use GCP with writer frozen and DR readiness disabled."
  }
}

variable "service_account_email" {
  type = string
}
