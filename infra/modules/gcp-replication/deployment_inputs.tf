variable "project_number" {
  type = string
  validation {
    condition     = length(trimspace(var.project_number)) > 0 && !can(regex("(?i)REPLACE|PLACEHOLDER|CHANGEME", var.project_number))
    error_message = "Supply a real deployment value for project_number."
  }
}
