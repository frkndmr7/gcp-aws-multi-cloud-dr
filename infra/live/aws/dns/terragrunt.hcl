include "root" {
  expose = true
  path   = find_in_parent_folders("root.hcl")
}

dependency "web" {
  config_path = "../web"
}

terraform {
  source = "${get_repo_root()}/infra/modules/aws-dns-failover"
}

inputs = {
  primary_health_disabled    = false
  primary_health_inverted    = false
  enable_dns_records         = true
  aws_region                 = include.root.locals.config.aws_region
  aws_account_id             = include.root.locals.config.aws_account_id
  hosted_zone_id             = include.root.locals.config.hosted_zone_id
  hostname                   = include.root.locals.config.hostname
  primary_ipv4               = include.root.locals.config.primary_ipv4
  cloudfront_distribution_id = dependency.web.outputs.cloudfront_distribution_id
}
