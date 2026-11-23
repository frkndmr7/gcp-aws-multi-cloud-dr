terraform {
  required_version = ">= 1.5.0, < 2.0.0"
  required_providers {
    google = { source = "hashicorp/google", version = "= 8.11.0" }
  }
}
provider "google" {
  project = var.project_id
  region  = var.region
}
resource "google_iam_workload_identity_pool" "failback" {
  project                   = var.project_id
  workload_identity_pool_id = "mcdr-aws-failback"
  display_name              = "AWS failback"
}
resource "google_iam_workload_identity_pool_provider" "aws" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.failback.workload_identity_pool_id
  workload_identity_pool_provider_id = "aws-failback"
  attribute_mapping = {
    "google.subject"     = "assertion.arn"
    "attribute.aws_role" = "assertion.arn.extract('assumed-role/{role}/')"
  }
  attribute_condition = "assertion.account == '${var.aws_account_id}' && assertion.arn.startsWith('arn:aws:sts::${var.aws_account_id}:assumed-role/${var.aws_role_name}/') && attribute.aws_role == '${var.aws_role_name}'"
  aws { account_id = var.aws_account_id }
}
resource "google_service_account" "failback" {
  project      = var.project_id
  account_id   = "mcdr-aws-failback"
  display_name = "AWS failback federation"
}
resource "google_service_account_iam_member" "federated_role" {
  service_account_id = google_service_account.failback.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.failback.name}/attribute.aws_role/${var.aws_role_name}"
}
resource "google_project_iam_custom_role" "firestore" {
  project     = var.project_id
  role_id     = "mcdrFailbackFirestore"
  title       = "MCDR failback Firestore access"
  description = "Point-read only for identity probe; create requires separate approval."
  permissions = concat(["datastore.entities.get"], var.enable_firestore_create ? ["datastore.entities.create"] : [])
}
resource "google_project_iam_member" "firestore" {
  project = var.project_id
  role    = google_project_iam_custom_role.firestore.name
  member  = "serviceAccount:${google_service_account.failback.email}"
}
output "pool_name" { value = google_iam_workload_identity_pool.failback.name }
output "provider_name" { value = google_iam_workload_identity_pool_provider.aws.name }
output "service_account_email" { value = google_service_account.failback.email }
