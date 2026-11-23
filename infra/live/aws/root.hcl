locals {
  raw_config = jsondecode(file("${get_repo_root()}/infra/local.json"))
  config     = alltrue([for value in values(local.raw_config) : length(trimspace(value)) > 0 && !can(regex("(?i)REPLACE|PLACEHOLDER|CHANGEME", value))]) ? local.raw_config : jsondecode(file("${get_repo_root()}/infra/INVALID_LOCAL_CONFIGURATION"))
}
# The state bucket is provisioned separately; generating this backend never creates it.
generate "backend" {
  path      = "backend.tf"
  if_exists = "overwrite_terragrunt"
  contents  = <<BACKEND
terraform {
  backend "s3" {
    bucket       = "${local.config.aws_state_bucket}"
    key          = "gcp-aws/${path_relative_to_include()}/terraform.tfstate"
    region       = "${local.config.aws_region}"
    use_lockfile = true
    encrypt      = true
  }
}
BACKEND
}
