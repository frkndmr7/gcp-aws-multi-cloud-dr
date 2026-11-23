include "root" {
  expose = true
  path   = find_in_parent_folders("root.hcl")
}
terraform { source = "${get_repo_root()}/infra/modules/aws-publisher-federation" }
dependency "replication" { config_path = "../replication" }
inputs = {
  aws_region     = include.root.locals.config.aws_region
  aws_account_id = include.root.locals.config.aws_account_id

  google_service_account_id = include.root.locals.config.google_service_account_id
  queue_arn                 = dependency.replication.outputs.queue_arn
}
