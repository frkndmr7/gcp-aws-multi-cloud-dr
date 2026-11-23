variable "aws_region" { type = string }
variable "aws_account_id" { type = string }
variable "hosted_zone_id" { type = string }
variable "hostname" { type = string }
variable "primary_ipv4" { type = string }
variable "cloudfront_distribution_id" { type = string }

variable "enable_dns_records" {
  type    = bool
  default = false
}

variable "primary_health_inverted" {
  type    = bool
  default = false
}

variable "primary_health_disabled" {
  type    = bool
  default = false
}
