terraform {
  required_version = ">= 1.5.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.24.0"
    }
  }
}

provider "aws" {
  region              = var.aws_region
  allowed_account_ids = [var.aws_account_id]
}

data "aws_route53_zone" "existing" {
  zone_id      = var.hosted_zone_id
  private_zone = false
}

data "aws_cloudfront_distribution" "secondary" {
  id = var.cloudfront_distribution_id
}

resource "aws_route53_health_check" "primary" {
  ip_address         = var.primary_ipv4
  invert_healthcheck = var.primary_health_inverted
  disabled           = var.primary_health_disabled
  fqdn               = var.hostname
  port               = 443
  type               = "HTTPS"
  resource_path      = "/health/live"
  enable_sni         = true
  request_interval   = 30
  failure_threshold  = 3
  tags               = { Name = "mcdr-gcp-primary-live" }
}

resource "aws_route53_health_check" "secondary" {
  fqdn              = data.aws_cloudfront_distribution.secondary.domain_name
  port              = 443
  type              = "HTTPS"
  resource_path     = "/health/live"
  enable_sni        = true
  request_interval  = 30
  failure_threshold = 3
  tags              = { Name = "mcdr-aws-secondary-live" }
}

resource "aws_route53_record" "primary" {
  count           = var.enable_dns_records ? 1 : 0
  zone_id         = data.aws_route53_zone.existing.zone_id
  name            = var.hostname
  type            = "A"
  ttl             = 60
  records         = [var.primary_ipv4]
  set_identifier  = "gcp-primary"
  health_check_id = aws_route53_health_check.primary.id
  failover_routing_policy { type = "PRIMARY" }
}

resource "aws_route53_record" "secondary" {
  count           = var.enable_dns_records ? 1 : 0
  zone_id         = data.aws_route53_zone.existing.zone_id
  name            = var.hostname
  type            = "A"
  set_identifier  = "aws-secondary"
  health_check_id = aws_route53_health_check.secondary.id
  failover_routing_policy { type = "SECONDARY" }
  alias {
    name                   = data.aws_cloudfront_distribution.secondary.domain_name
    zone_id                = data.aws_cloudfront_distribution.secondary.hosted_zone_id
    evaluate_target_health = false
  }
}
