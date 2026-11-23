variable "aws_region" { type = string }
variable "aws_account_id" { type = string }
variable "zip_path" { type = string }
variable "stream_arn" {
  type = string
  validation {
    condition     = can(regex("^arn:aws:dynamodb:[a-z0-9-]+:[0-9]{12}:table/[A-Za-z0-9_.-]+/stream/[0-9T:.-]+$", var.stream_arn))
    error_message = "Use the actual stream ARN from the target table."
  }
}

variable "mapping_enabled" {
  type    = bool
  default = false
}
