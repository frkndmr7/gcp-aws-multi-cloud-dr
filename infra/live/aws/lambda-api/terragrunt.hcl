include "root" {
  expose = true
  path   = find_in_parent_folders("root.hcl")
}

dependency "dynamodb" {
  config_path = "../dynamodb"
}

terraform {
  source = "${get_repo_root()}/infra/modules/aws-lambda-api"
}

inputs = {
  aws_region                   = include.root.locals.config.aws_region
  aws_account_id               = include.root.locals.config.aws_account_id
  table_name                   = dependency.dynamodb.outputs.table_name
  table_arn                    = dependency.dynamodb.outputs.table_arn
  enable_writer_permission     = true
  writer_mode                  = "standby"
  shorten_authorization_type   = "AWS_IAM"
  disable_execute_api_endpoint = false
  lambda_zip_path              = get_env("LAMBDA_ZIP_PATH", "")
}
