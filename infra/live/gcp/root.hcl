locals {
  raw_config = jsondecode(file("${get_repo_root()}/infra/local.json"))
  config     = alltrue([for value in values(local.raw_config) : length(trimspace(value)) > 0 && !can(regex("(?i)REPLACE|PLACEHOLDER|CHANGEME", value))]) ? local.raw_config : jsondecode(file("${get_repo_root()}/infra/INVALID_LOCAL_CONFIGURATION"))
}
# The bucket is provisioned separately; this block does not create or configure it.
generate "backend" {
  path      = "backend.tf"
  if_exists = "overwrite_terragrunt"
  contents  = <<EOF
terraform {
  backend "gcs" {
    bucket = "${local.config.gcp_state_bucket}"
    prefix = "gcp/${path_relative_to_include()}"
  }
}
EOF
}
