variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "eu-central-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "allowed_alb_cidrs" {
  description = "CIDR blocks allowed to access the public ALB (HTTPS)"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}
