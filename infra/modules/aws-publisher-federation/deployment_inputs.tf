variable "aws_region" {
  type = string
  validation {
    condition     = length(trimspace(var.aws_region)) > 0 && !can(regex("(?i)REPLACE|PLACEHOLDER|CHANGEME", var.aws_region))
    error_message = "Supply a real deployment value for aws_region."
  }
}
variable "aws_account_id" {
  type = string
  validation {
    condition     = length(trimspace(var.aws_account_id)) > 0 && !can(regex("(?i)REPLACE|PLACEHOLDER|CHANGEME", var.aws_account_id))
    error_message = "Supply a real deployment value for aws_account_id."
  }
}
