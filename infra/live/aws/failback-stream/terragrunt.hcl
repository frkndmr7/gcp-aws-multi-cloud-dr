include "root" {
  expose = true
  path   = find_in_parent_folders("root.hcl")
}
terraform { source = "${get_repo_root()}/infra/modules/aws-failback-stream" }
inputs = {
  table_name          = include.root.locals.config.table_name
  gcp_project_id      = include.root.locals.config.project_id
  gcp_project_number  = include.root.locals.config.project_number
  wif_pool            = include.root.locals.config.wif_pool
  wif_provider        = include.root.locals.config.wif_provider
  gcp_service_account = include.root.locals.config.failback_service_account

  mapping_enabled = false
  aws_region      = include.root.locals.config.aws_region
  aws_account_id  = include.root.locals.config.aws_account_id
  stream_arn      = include.root.locals.config.stream_arn
  zip_path        = get_env("FAILBACK_ZIP_PATH", "")
}
