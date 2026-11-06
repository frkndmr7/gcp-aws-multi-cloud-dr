include "root" {
  path = find_in_parent_folders("root.hcl")
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
  project_id            = get_env("GCP_PROJECT_ID", "")
  region                = get_env("GCP_REGION", "")
  image                 = get_env("GCP_CONTAINER_IMAGE", "")
  service_account_email = dependency.iam.outputs.cloud_run_service_account_email
}
