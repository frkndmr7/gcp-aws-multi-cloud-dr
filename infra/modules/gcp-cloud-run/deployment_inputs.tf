variable "domain_name" {
  type = string
  validation {
    condition     = length(trimspace(var.domain_name)) > 0 && !can(regex("(?i)REPLACE|PLACEHOLDER|CHANGEME", var.domain_name))
    error_message = "Supply a real deployment value for domain_name."
  }
}
