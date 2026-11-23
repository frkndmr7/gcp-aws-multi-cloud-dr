include "root" {
  expose = true
  path   = find_in_parent_folders("root.hcl")
}
terraform { source = "${get_repo_root()}/infra/modules/aws-failback-identity" }
inputs = {
  aws_region     = include.root.locals.config.aws_region
  aws_account_id = include.root.locals.config.aws_account_id
}
