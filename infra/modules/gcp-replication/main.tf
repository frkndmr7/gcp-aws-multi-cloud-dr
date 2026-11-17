resource "google_project_service" "eventarc" {
  for_each           = var.enable_publisher_stack && var.enable_publisher_service ? toset(["eventarc.googleapis.com"]) : toset([])
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}
resource "google_service_account" "publisher" {
  project      = var.project_id
  account_id   = "mcdr-event-publisher"
  display_name = "MCDR Event Publisher"
}
resource "google_service_account" "eventarc" {
  count        = var.enable_publisher_stack && var.enable_publisher_service ? 1 : 0
  project      = var.project_id
  account_id   = "mcdr-eventarc-invoker"
  display_name = "MCDR Eventarc Invoker"
}
resource "google_project_iam_member" "event_receiver" {
  count   = var.enable_publisher_stack && var.enable_publisher_service ? 1 : 0
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.eventarc[0].email}"
}
resource "google_cloud_run_v2_service" "publisher" {
  count               = var.enable_publisher_service ? 1 : 0
  project             = var.project_id
  location            = var.region
  name                = "mcdr-event-publisher"
  ingress             = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  deletion_protection = true
  template {
    service_account = google_service_account.publisher.email
    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }
    containers {
      image = var.publisher_image
      env {
        name  = "PUBLISHER_ENABLED"
        value = tostring(var.enable_publisher)
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "AWS_ROLE_ARN"
        value = var.aws_role_arn
      }
      env {
        name  = "AWS_TOKEN_AUDIENCE"
        value = var.token_audience
      }
      env {
        name  = "AWS_REGION"
        value = var.aws_region
      }
      env {
        name  = "SQS_QUEUE_URL"
        value = var.queue_url
      }
    }
  }
}
resource "google_cloud_run_v2_service_iam_member" "eventarc_invoker" {
  count    = var.enable_publisher_stack && var.enable_publisher_service ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.publisher[0].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.eventarc[0].email}"
}
resource "google_eventarc_trigger" "firestore_create" {
  count    = var.enable_publisher_stack && var.enable_publisher_service && var.enable_eventarc ? 1 : 0
  name     = "mcdr-firestore-create"
  project  = var.project_id
  location = var.region
  matching_criteria {
    attribute = "type"
    value     = "google.cloud.firestore.document.v1.created"
  }
  matching_criteria {
    attribute = "database"
    value     = "(default)"
  }
  matching_criteria {
    attribute = "document"
    operator  = "match-path-pattern"
    value     = "urls/{id}"
  }
  event_data_content_type = "application/protobuf"
  destination {
    cloud_run_service {
      service = google_cloud_run_v2_service.publisher[0].name
      region  = var.region
      path    = "/"
    }
  }
  service_account = google_service_account.eventarc[0].email
  depends_on      = [google_project_service.eventarc, google_project_iam_member.event_receiver, google_cloud_run_v2_service_iam_member.eventarc_invoker]
}
