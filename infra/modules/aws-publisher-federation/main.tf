terraform {
  required_version = ">= 1.5.0, < 2.0.0"
  required_providers { aws = { source = "hashicorp/aws", version = "= 6.24.0" } }
}
provider "aws" {
  region              = "eu-west-1"
  allowed_account_ids = ["109678733855"]
}
variable "google_service_account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{10,30}$", var.google_service_account_id))
    error_message = "Provide a verified numeric Google service account unique ID."
  }
}
variable "queue_arn" { type = string }
resource "aws_iam_role" "publisher" {
  name               = "mcdr-gcp-aws-publisher"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Federated = "accounts.google.com" }, Action = "sts:AssumeRoleWithWebIdentity", Condition = { StringEquals = { "accounts.google.com:aud" = var.google_service_account_id, "accounts.google.com:sub" = var.google_service_account_id, "accounts.google.com:oaud" = "sts.amazonaws.com" } } }] })
}
resource "aws_iam_role_policy" "publisher" {
  name   = "sqs-send-only"
  role   = aws_iam_role.publisher.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = "sqs:SendMessage", Resource = var.queue_arn }] })
}
output "role_arn" { value = aws_iam_role.publisher.arn }
