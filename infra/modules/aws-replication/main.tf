resource "aws_sqs_queue" "dlq" {
  name                      = "mcdr-gcp-aws-replication-dlq"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true
}
resource "aws_sqs_queue" "main" {
  name                       = "mcdr-gcp-aws-replication"
  message_retention_seconds  = 345600
  visibility_timeout_seconds = 120
  sqs_managed_sse_enabled    = true
  redrive_policy             = jsonencode({ deadLetterTargetArn = aws_sqs_queue.dlq.arn, maxReceiveCount = 5 })
}
resource "aws_cloudwatch_log_group" "consumer" {
  name              = "/aws/lambda/mcdr-gcp-aws-replication"
  retention_in_days = 7
}
resource "aws_iam_role" "consumer" {
  name               = "mcdr-gcp-aws-replication-consumer"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}
resource "aws_iam_role_policy" "consumer" {
  name = "sqs-dynamodb-logs"
  role = aws_iam_role.consumer.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"], Resource = aws_sqs_queue.main.arn },
    { Effect = "Allow", Action = ["dynamodb:GetItem", "dynamodb:PutItem"], Resource = var.table_arn },
    { Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = "${aws_cloudwatch_log_group.consumer.arn}:*" }
  ] })
}
resource "aws_lambda_function" "consumer" {
  function_name    = "mcdr-gcp-aws-replication"
  role             = aws_iam_role.consumer.arn
  runtime          = "python3.12"
  handler          = "consumer.handler"
  architectures    = ["x86_64"]
  filename         = var.lambda_zip_path
  source_code_hash = filebase64sha256(var.lambda_zip_path)
  timeout          = 15
  memory_size      = 256
  environment { variables = { DYNAMODB_TABLE = var.table_name } }
  depends_on = [aws_iam_role_policy.consumer]
}
resource "aws_lambda_event_source_mapping" "sqs" {
  event_source_arn        = aws_sqs_queue.main.arn
  function_name           = aws_lambda_function.consumer.arn
  batch_size              = 10
  enabled                 = var.enable_consumer_mapping
  function_response_types = ["ReportBatchItemFailures"]
}
