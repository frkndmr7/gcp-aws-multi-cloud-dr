# Disabled by default. A real operator CIDR and a separate approval are required.
resource "google_compute_security_policy" "operator_gate" {
  count   = var.enable_operator_write_gate ? 1 : 0
  project = var.project_id
  name    = "mcdr-primary-operator-write-gate"

  lifecycle {
    precondition {
      condition     = var.operator_cidr != ""
      error_message = "Supply a verified operator CIDR before enabling the gate."
    }
  }
  rule {
    priority = 1000
    action   = "deny(403)"
    match {
      expr {
        expression = "request.method != 'GET' && request.method != 'HEAD' && request.method != 'OPTIONS' && !inIpRange(origin.ip, '${var.operator_cidr}')"
      }
    }
  }
  rule {
    priority = 2147483647
    action   = "allow"
    match {
      versioned_expr = "SRC_IPS_V1"
      config { src_ip_ranges = ["*"] }
    }
  }
}
