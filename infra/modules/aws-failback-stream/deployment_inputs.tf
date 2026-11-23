variable "table_name" {
  type = string
  validation {
    condition     = length(trimspace(var.table_name)) > 0 && !can(regex("(?i)REPLACE|PLACEHOLDER|CHANGEME", var.table_name))
    error_message = "Supply a real deployment value for table_name."
  }
}
variable "gcp_project_id" {
  type = string
  validation {
    condition     = length(trimspace(var.gcp_project_id)) > 0 && !can(regex("(?i)REPLACE|PLACEHOLDER|CHANGEME", var.gcp_project_id))
    error_message = "Supply a real deployment value for gcp_project_id."
  }
}
variable "gcp_project_number" {
  type = string
  validation {
    condition     = length(trimspace(var.gcp_project_number)) > 0 && !can(regex("(?i)REPLACE|PLACEHOLDER|CHANGEME", var.gcp_project_number))
    error_message = "Supply a real deployment value for gcp_project_number."
  }
}
variable "wif_pool" {
  type = string
  validation {
    condition     = length(trimspace(var.wif_pool)) > 0 && !can(regex("(?i)REPLACE|PLACEHOLDER|CHANGEME", var.wif_pool))
    error_message = "Supply a real deployment value for wif_pool."
  }
}
variable "wif_provider" {
  type = string
  validation {
    condition     = length(trimspace(var.wif_provider)) > 0 && !can(regex("(?i)REPLACE|PLACEHOLDER|CHANGEME", var.wif_provider))
    error_message = "Supply a real deployment value for wif_provider."
  }
}
variable "gcp_service_account" {
  type = string
  validation {
    condition     = length(trimspace(var.gcp_service_account)) > 0 && !can(regex("(?i)REPLACE|PLACEHOLDER|CHANGEME", var.gcp_service_account))
    error_message = "Supply a real deployment value for gcp_service_account."
  }
}
