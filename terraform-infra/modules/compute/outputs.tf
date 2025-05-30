output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.main.id
}

output "instance_arn" {
  description = "ARN of the EC2 instance"
  value       = aws_instance.main.arn
}

output "private_ip" {
  description = "Private IP address of the EC2 instance"
  value       = aws_instance.main.private_ip
}

output "public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_instance.main.public_ip
}

output "availability_zone" {
  description = "Availability zone of the EC2 instance"
  value       = aws_instance.main.availability_zone
}

output "ebs_volume_id" {
  description = "ID of the additional EBS volume"
  value       = aws_ebs_volume.app_data.id
}
