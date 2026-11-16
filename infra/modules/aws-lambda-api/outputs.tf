output "function_name" {
  value = aws_lambda_function.secondary.function_name
}
output "function_arn" {
  value = aws_lambda_function.secondary.arn
}
output "api_endpoint" {
  value = aws_apigatewayv2_api.secondary.api_endpoint
}
