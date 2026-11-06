include "root" {
  path = find_in_parent_folders("root.hcl")
}
terraform {
  source = "${get_repo_root()}/infra/modules/gcp-firestore"
}
dependencies {
  paths = ["../iam"]
}
inputs = {
  project_id         = get_env("GCP_PROJECT_ID", "")
  region             = get_env("GCP_REGION", "")
  firestore_location = get_env("GCP_FIRESTORE_LOCATION", "")
}
