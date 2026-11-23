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
resource "aws_iam_role_policy" "stream_read" {
  lifecycle {
    precondition {
      condition     = startswith(var.stream_arn, "arn:aws:dynamodb:${var.aws_region}:${var.aws_account_id}:table/${var.table_name}/stream/")
      error_message = "Stream must belong to the configured account, region and table."
    }
  }
  name = "failback-stream-read"
  role = "mcdr-gcp-aws-failback-lambda"
  policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Action = ["dynamodb:DescribeStream", "dynamodb:GetRecords", "dynamodb:GetShardIterator"], Resource = var.stream_arn
  }] })
}
resource "aws_lambda_function" "failback" {
  function_name    = "mcdr-gcp-aws-failback"
  role             = "arn:aws:iam::${var.aws_account_id}:role/mcdr-gcp-aws-failback-lambda"
  runtime          = "python3.12"
  handler          = "functions.failback_identity.handler.handler"
  architectures    = ["x86_64"]
  filename         = var.zip_path
  source_code_hash = filebase64sha256(var.zip_path)
  timeout          = 30
  memory_size      = 256
  environment {
    variables = {
      MCDR_AWS_ACCOUNT_ID      = var.aws_account_id
      MCDR_GCP_PROJECT_ID      = var.gcp_project_id
      MCDR_GCP_PROJECT_NUMBER  = var.gcp_project_number
      MCDR_WIF_POOL            = var.wif_pool
      MCDR_WIF_PROVIDER        = var.wif_provider
      MCDR_GCP_SERVICE_ACCOUNT = var.gcp_service_account
      MCDR_AWS_ROLE_NAME       = "mcdr-gcp-aws-failback-lambda"
    }
  }
}
resource "aws_lambda_event_source_mapping" "stream" {
  event_source_arn               = var.stream_arn
  function_name                  = aws_lambda_function.failback.arn
  enabled                        = var.mapping_enabled
  starting_position              = "TRIM_HORIZON"
  batch_size                     = 10
  function_response_types        = ["ReportBatchItemFailures"]
  maximum_retry_attempts         = 5
  bisect_batch_on_function_error = true
  depends_on                     = [aws_iam_role_policy.stream_read]
}
