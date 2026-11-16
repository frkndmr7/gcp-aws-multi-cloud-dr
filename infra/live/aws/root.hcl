# The state bucket is provisioned separately; generating this backend never creates it.
generate "backend" {
  path      = "backend.tf"
  if_exists = "overwrite_terragrunt"
  contents  = <<BACKEND
terraform {
  backend "s3" {
    bucket       = "gcp-aws-mcdr-tfstate-109678733855-eu-west-1"
    key          = "gcp-aws/${path_relative_to_include()}/terraform.tfstate"
    region       = "eu-west-1"
    use_lockfile = true
    encrypt      = true
  }
}
BACKEND
}
