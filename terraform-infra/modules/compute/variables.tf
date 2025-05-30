variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "instance_name" {
  description = "Name suffix for the instance"
  type        = string
}

variable "ami_id" {
  description = "AMI ID for the instance"
  type        = string
}

variable "instance_type" {
  description = "Instance type"
  type        = string
}

variable "key_name" {
  description = "Key pair name"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID to launch the instance in"
  type        = string
}

variable "vpc_security_group_ids" {
  description = "List of security group IDs"
  type        = list(string)
}

variable "ebs_volume_size" {
  description = "Size of the EBS volume in GB"
  type        = number
}

variable "ebs_volume_type" {
  description = "Type of EBS volume"
  type        = string
}

variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring"
  type        = bool
}

variable "user_data_script" {
  description = "Comma-separated list of user data scripts to execute"
  type        = string
  default     = ""
}
