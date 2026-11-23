include "root" {
  expose = true
  path   = find_in_parent_folders("root.hcl")
}
terraform {
  source = "${get_repo_root()}/infra/modules/gcp-artifact-registry"
}
inputs = {
  project_id = include.root.locals.config.project_id
  region     = include.root.locals.config.gcp_region
}
