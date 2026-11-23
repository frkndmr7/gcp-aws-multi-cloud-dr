include "root" {
  expose = true
  path   = find_in_parent_folders("root.hcl")
}
terraform { source = "${get_repo_root()}/infra/modules/gcp-replication" }
dependencies { paths = ["../firestore", "../iam"] }
inputs = {
  project_number = include.root.locals.config.project_number

  project_id               = include.root.locals.config.project_id
  region                   = include.root.locals.config.gcp_region
  publisher_image          = include.root.locals.config.publisher_image
  aws_role_arn             = include.root.locals.config.aws_role_arn
  queue_url                = include.root.locals.config.queue_url
  enable_publisher_service = true
  enable_publisher_stack   = true
  enable_publisher         = true
  enable_eventarc          = true
  aws_region               = include.root.locals.config.aws_region
  token_audience           = "sts.amazonaws.com"
}
