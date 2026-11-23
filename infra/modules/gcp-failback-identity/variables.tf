variable "project_id" { type = string }
variable "region" { type = string }
variable "aws_account_id" { type = string }
variable "aws_role_name" { type = string }
variable "enable_firestore_create" {
  type    = bool
  default = false
}
