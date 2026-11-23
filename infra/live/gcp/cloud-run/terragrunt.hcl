include "root" {
  expose = true
  path   = find_in_parent_folders("root.hcl")
}
terraform {
  source = "${get_repo_root()}/infra/modules/gcp-cloud-run"
}
dependency "iam" {
  config_path = "../iam"
}
dependencies {
  paths = ["../firestore"]
}
inputs = {
  domain_name = include.root.locals.config.hostname

  project_id            = include.root.locals.config.project_id
  region                = include.root.locals.config.gcp_region
  image                 = include.root.locals.config.app_image
  invoker_iam_disabled  = true
  service_account_email = dependency.iam.outputs.cloud_run_service_account_email
}
