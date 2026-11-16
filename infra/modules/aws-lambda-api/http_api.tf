resource "aws_apigatewayv2_api" "secondary" {
  name                         = "mcdr-gcp-aws-secondary"
  protocol_type                = "HTTP"
  disable_execute_api_endpoint = true
}

resource "aws_apigatewayv2_integration" "secondary" {
  api_id                 = aws_apigatewayv2_api.secondary.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.secondary.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "application" {
  for_each = toset([
    "GET /api/status",
    "POST /api/shorten",
    "GET /r/{code}",
    "GET /health/live",
    "GET /health/dr"
  ])
  api_id    = aws_apigatewayv2_api.secondary.id
  route_key = each.value
  target    = "integrations/${aws_apigatewayv2_integration.secondary.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.secondary.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowSecondaryHttpApi"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.secondary.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.secondary.execution_arn}/*/*/*"
}
