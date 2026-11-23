variable "aws_region" {
  type = string
}
variable "aws_account_id" {
  type = string
}
variable "table_name" {
  type = string
}
variable "table_arn" {
  type = string
}
variable "lambda_zip_path" {
  type = string
  validation {
    condition     = startswith(var.lambda_zip_path, "/") && fileexists(var.lambda_zip_path)
    error_message = "Set LAMBDA_ZIP_PATH to an existing absolute Lambda ZIP path."
  }
}

variable "disable_execute_api_endpoint" {
  type    = bool
  default = true
}

variable "enable_writer_permission" {
  type    = bool
  default = false
}

variable "writer_mode" {
  type    = string
  default = "standby"
  validation {
    condition     = contains(["standby", "active", "frozen"], var.writer_mode)
    error_message = "writer_mode must be standby, active, or frozen."
  }
}

variable "shorten_authorization_type" {
  description = "POST authorization; NONE is only for a separately approved short demo."
  type        = string
  default     = "AWS_IAM"
  validation {
    condition     = contains(["AWS_IAM", "NONE"], var.shorten_authorization_type)
    error_message = "Use AWS_IAM or NONE."
  }
}
