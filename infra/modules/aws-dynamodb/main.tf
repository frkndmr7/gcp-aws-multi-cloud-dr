resource "aws_dynamodb_table" "urls" {
  name                        = var.table_name
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "id"
  deletion_protection_enabled = true
  stream_enabled              = var.stream_enabled
  stream_view_type            = var.stream_enabled ? "NEW_IMAGE" : null

  attribute {
    name = "id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = false
  }

  lifecycle {
    prevent_destroy = true
  }
}
