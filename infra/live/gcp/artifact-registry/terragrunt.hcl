include "root" {
  path = find_in_parent_folders("root.hcl")
}
terraform {
  source = "${get_repo_root()}/infra/modules/gcp-artifact-registry"
}
inputs = {
  project_id = get_env("GCP_PROJECT_ID", "")
  region     = get_env("GCP_REGION", "")
}
