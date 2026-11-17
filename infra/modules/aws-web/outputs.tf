output "certificate_arn" {
  value = aws_acm_certificate.frontend.arn
}

output "certificate_domain_validation_options" {
  value = aws_acm_certificate.frontend.domain_validation_options
}

output "frontend_bucket_name" {
  value = aws_s3_bucket.frontend.bucket
}

output "cloudfront_domain_name" {
  value = aws_cloudfront_distribution.frontend.domain_name
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.frontend.id
}
