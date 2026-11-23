include "root" {
  expose = true
  path   = find_in_parent_folders("root.hcl")
}

dependency "lambda_api" {
  config_path = "../lambda-api"
}

terraform {
  source = "${get_repo_root()}/infra/modules/aws-web"
}

inputs = {
  aws_region           = include.root.locals.config.aws_region
  aws_account_id       = include.root.locals.config.aws_account_id
  domain_name          = include.root.locals.config.hostname
  frontend_bucket_name = include.root.locals.config.frontend_bucket_name
  api_endpoint         = dependency.lambda_api.outputs.api_endpoint
}
