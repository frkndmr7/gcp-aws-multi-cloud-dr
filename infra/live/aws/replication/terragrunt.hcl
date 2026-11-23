include "root" {
  expose = true
  path   = find_in_parent_folders("root.hcl")
}
dependency "dynamodb" { config_path = "../dynamodb" }
terraform { source = "${get_repo_root()}/infra/modules/aws-replication" }
inputs = {
  aws_region              = include.root.locals.config.aws_region
  enable_consumer_mapping = true
  aws_account_id          = include.root.locals.config.aws_account_id
  table_name              = dependency.dynamodb.outputs.table_name
  table_arn               = dependency.dynamodb.outputs.table_arn
  lambda_zip_path         = get_env("REPLICATION_CONSUMER_ZIP", "")
}
