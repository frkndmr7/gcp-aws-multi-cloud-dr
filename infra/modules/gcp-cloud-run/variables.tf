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
    SERVING_PROVIDER   = "gcp"
    CLOUD_ROLE         = "primary"
    WRITER_MODE        = "frozen"
    DR_READY           = "false"
    REPOSITORY_BACKEND = "firestore"
  }
  validation {
    condition     = lookup(var.environment, "SERVING_PROVIDER", "") == "gcp" && contains(["frozen", "active"], lookup(var.environment, "WRITER_MODE", "")) && lookup(var.environment, "DR_READY", "") == "false" && lookup(var.environment, "REPOSITORY_BACKEND", "") == "firestore"
    error_message = "Use GCP with writer frozen or active, DR readiness disabled, and Firestore selected."
  }
}

variable "service_account_email" {
  type = string
}

variable "invoker_iam_disabled" {
  type    = bool
  default = false
}

variable "enable_operator_write_gate" {
  description = "Plan an IP-restricted write gate before enabling the writer."
  type        = bool
  default     = false
}

variable "operator_cidr" {
  description = "Operator public IPv4 CIDR; required when the gate is enabled."
  type        = string
  default     = ""
  validation {
    condition     = var.operator_cidr == "" || (can(cidrhost(var.operator_cidr, 0)) && !strcontains(var.operator_cidr, ":") && endswith(var.operator_cidr, "/32"))
    error_message = "operator_cidr must be a single IPv4 /32."
  }
}
