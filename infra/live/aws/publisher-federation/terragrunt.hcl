include "root" { path = find_in_parent_folders("root.hcl") }
terraform { source = "${get_repo_root()}/infra/modules/aws-publisher-federation" }
dependency "replication" { config_path = "../replication" }
inputs = {
  google_service_account_id = "106917172353804245450"
  queue_arn                 = dependency.replication.outputs.queue_arn
}
