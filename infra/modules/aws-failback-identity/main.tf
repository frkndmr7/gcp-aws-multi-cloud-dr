terraform {
  required_version = ">= 1.5.0, < 2.0.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "= 6.24.0" }
  }
}
provider "aws" {
  region              = var.aws_region
  allowed_account_ids = [var.aws_account_id]
}
resource "aws_iam_role" "failback" {
  name = "mcdr-gcp-aws-failback-lambda"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}
output "role_arn" { value = aws_iam_role.failback.arn }

resource "aws_cloudwatch_log_group" "probe" {
  name              = "/aws/lambda/mcdr-gcp-aws-failback"
  retention_in_days = 7
}
resource "aws_iam_role_policy" "probe_logs" {
  name = "failback-probe-logs"
  role = aws_iam_role.failback.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "${aws_cloudwatch_log_group.probe.arn}:*"
    }]
  })
}
