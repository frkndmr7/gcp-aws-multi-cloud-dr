include "root" {
  expose = true
  path   = find_in_parent_folders("root.hcl")
}

terraform {
  source = "${get_repo_root()}/infra/modules/aws-dynamodb"
}

inputs = {
  aws_region     = include.root.locals.config.aws_region
  aws_account_id = include.root.locals.config.aws_account_id
  table_name     = include.root.locals.config.table_name
  stream_enabled = true
}
