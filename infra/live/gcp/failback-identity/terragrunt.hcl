include "root" {
  expose = true
  path   = find_in_parent_folders("root.hcl")
}
terraform { source = "${get_repo_root()}/infra/modules/gcp-failback-identity" }
inputs = {
  project_id              = include.root.locals.config.project_id
  region                  = include.root.locals.config.gcp_region
  aws_account_id          = include.root.locals.config.aws_account_id
  aws_role_name           = include.root.locals.config.aws_role_name
  enable_firestore_create = true
}
