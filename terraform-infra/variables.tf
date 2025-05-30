# Project Configuration
variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "devops-portfolio"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "owner" {
  description = "Resource owner"
  type        = string
  default     = "DevOps-Engineer"
}

# AWS Configuration
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-central-1"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["eu-central-1a", "eu-central-1b"]
}

# Deployment Control
variable "deploy_database" {
  description = "Whether to deploy the database instance"
  type        = bool
  default     = false
}

# Instance Configuration
variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
  
  validation {
    condition = can(regex("^(t3|t2|m5|m4|c5|c4)\\.(nano|micro|small|medium|large|xlarge|2xlarge)$", var.instance_type))
    error_message = "Instance type must be a valid EC2 instance type (e.g., t3.medium, m5.large)."
  }
}

variable "key_pair_name" {
  description = "Name of the AWS key pair for EC2 access"
  type        = string
  default     = ""
}

# Network Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.20.0/24"]
}

# Storage Configuration
variable "ebs_volume_size" {
  description = "Size of EBS volumes in GB"
  type        = number
  default     = 30
  
  validation {
    condition     = var.ebs_volume_size >= 20 && var.ebs_volume_size <= 1000
    error_message = "EBS volume size must be between 20 and 1000 GB."
  }
}

variable "ebs_volume_type" {
  description = "Type of EBS volume"
  type        = string
  default     = "gp3"
}

# Monitoring Configuration
variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring"
  type        = bool
  default     = true
}

# Security Configuration
variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the ALB"
  type        = list(string)
  default     = ["127.0.0.1/32"]
  
  validation {
    condition = alltrue([
      for cidr in var.allowed_cidr_blocks : can(cidrhost(cidr, 0))
    ])
    error_message = "All CIDR blocks must be valid (e.g., 10.0.0.0/16, 192.168.1.0/24)."
  }
}

variable "ssh_cidr_blocks" {
  description = "CIDR blocks allowed SSH access"
  type        = list(string)
  default     = ["127.0.0.1/32"]
}

# Application Configuration
variable "grafana_admin_password" {
  description = "Grafana admin password (stored in Parameter Store)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "postgres_password" {
  description = "PostgreSQL password (stored in Parameter Store)"
  type        = string
  default     = ""
  sensitive   = true
}
