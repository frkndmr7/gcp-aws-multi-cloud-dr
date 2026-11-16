variable "aws_region" {
  type = string
  validation {
    condition     = length(trimspace(var.aws_region)) > 0
    error_message = "An AWS region is required."
  }
}

variable "aws_account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "A 12-digit AWS account ID is required."
  }
}

variable "table_name" {
  type = string
  validation {
    condition     = can(regex("^[a-zA-Z0-9_.-]{3,255}$", var.table_name))
    error_message = "The table name must be 3-255 valid DynamoDB characters."
  }
}
