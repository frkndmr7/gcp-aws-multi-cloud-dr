variable "aws_region" {
  type = string
}

variable "aws_account_id" {
  type = string
}

variable "domain_name" {
  type = string
}

variable "frontend_bucket_name" {
  type = string
}

variable "api_endpoint" {
  type = string
  validation {
    condition     = can(regex("^https://[a-z0-9.-]+/?$", var.api_endpoint))
    error_message = "A valid HTTPS API Gateway endpoint without a path is required."
  }
}
