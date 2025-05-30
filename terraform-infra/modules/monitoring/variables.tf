variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "monitoring_instance_id" {
  description = "ID of the monitoring EC2 instance"
  type        = string
}

variable "database_instance_id" {
  description = "ID of the database EC2 instance (optional)"
  type        = string
  default     = ""
}

variable "database_private_ip" {
  description = "Private IP of the database instance"
  type        = string
  default     = ""
}

variable "deploy_database" {
  description = "Whether database is deployed"
  type        = bool
  default     = false
}
