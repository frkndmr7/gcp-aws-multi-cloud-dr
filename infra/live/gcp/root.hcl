# The bucket is provisioned separately; this block does not create or configure it.
generate "backend" {
  path      = "backend.tf"
  if_exists = "overwrite_terragrunt"
  contents  = <<EOF
terraform {
  backend "gcs" {
    bucket = "gcp-aws-multi-cloud-dr-tfstate"
    prefix = "gcp/${path_relative_to_include()}"
  }
}
EOF
}
