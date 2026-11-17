include "root" { path = find_in_parent_folders("root.hcl") }
terraform { source = "${get_repo_root()}/infra/modules/gcp-replication" }
dependencies { paths = ["../firestore", "../iam"] }
inputs = {
  project_id               = get_env("GCP_PROJECT_ID", "")
  region                   = get_env("GCP_REGION", "")
  publisher_image          = "europe-west1-docker.pkg.dev/gcp-aws-multi-cloud-dr/mcdr-images/mcdr-publisher@sha256:6ca313dde768ab12e2cda7fda67c25d723829d82f9837f2a9d76ff52efad9eb4"
  aws_role_arn             = "arn:aws:iam::109678733855:role/mcdr-gcp-aws-publisher"
  queue_url                = "https://sqs.eu-west-1.amazonaws.com/109678733855/mcdr-gcp-aws-replication"
  enable_publisher_service = true
  enable_publisher_stack   = true
  enable_publisher         = true
  enable_eventarc          = true
  aws_region               = "eu-west-1"
  token_audience           = "sts.amazonaws.com"
}
