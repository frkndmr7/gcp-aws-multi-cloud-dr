resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/mcdr-gcp-aws-secondary"
  retention_in_days = 7
}

resource "aws_iam_role" "lambda" {
  name = "mcdr-gcp-aws-secondary-lambda"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy" "lambda" {
  name = "dynamodb-read-and-logs"
  role = aws_iam_role.lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        { Effect = "Allow", Action = ["dynamodb:GetItem"], Resource = var.table_arn },
        { Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = "${aws_cloudwatch_log_group.lambda.arn}:*" }
      ],
      var.enable_writer_permission ? [{ Effect = "Allow", Action = ["dynamodb:PutItem"], Resource = var.table_arn }] : []
    )
  })
}

resource "aws_lambda_function" "secondary" {
  function_name    = "mcdr-gcp-aws-secondary"
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.12"
  handler          = "app.lambda_handler.handler"
  architectures    = ["x86_64"]
  filename         = var.lambda_zip_path
  source_code_hash = filebase64sha256(var.lambda_zip_path)
  memory_size      = 256
  timeout          = 15

  environment {
    variables = {
      SERVING_PROVIDER   = "aws"
      CLOUD_ROLE         = "secondary"
      WRITER_MODE        = var.writer_mode
      DR_READY           = "false"
      REPOSITORY_BACKEND = "dynamodb"
      DYNAMODB_TABLE     = var.table_name
    }
  }

  depends_on = [aws_iam_role_policy.lambda]
}
