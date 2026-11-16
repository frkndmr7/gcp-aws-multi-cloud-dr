output "table_name" {
  value = aws_dynamodb_table.urls.name
}

output "table_arn" {
  value = aws_dynamodb_table.urls.arn
}
