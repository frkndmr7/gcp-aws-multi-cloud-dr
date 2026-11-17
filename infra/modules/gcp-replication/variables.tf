variable "project_id" { type = string }
variable "region" { type = string }
variable "publisher_image" { type = string }
variable "aws_role_arn" { type = string }
variable "queue_url" { type = string }
variable "aws_region" { type = string }
variable "token_audience" { type = string }

variable "enable_eventarc" {
  type    = bool
  default = false
}

variable "enable_publisher" {
  type    = bool
  default = false
}

variable "enable_publisher_stack" {
  type    = bool
  default = false
}

variable "enable_publisher_service" {
  type    = bool
  default = false
}
