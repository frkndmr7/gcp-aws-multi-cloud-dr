include "root" {
  path = find_in_parent_folders("root.hcl")
}

dependency "lambda_api" {
  config_path = "../lambda-api"
}

terraform {
  source = "${get_repo_root()}/infra/modules/aws-web"
}

inputs = {
  aws_region           = "eu-west-1"
  aws_account_id       = "109678733855"
  domain_name          = "app.shorturldr.online"
  frontend_bucket_name = "mcdr-gcp-aws-web-109678733855-eu-west-1"
  api_endpoint         = dependency.lambda_api.outputs.api_endpoint
}
