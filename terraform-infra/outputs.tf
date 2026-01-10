output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = module.vpc.private_subnet_ids
}

output "alb_sg_id" {
  description = "ID of the ALB security group"
  value       = module.security.alb_sg_id
}

output "monitoring_sg_id" {
  description = "ID of the monitoring security group"
  value       = module.security.monitoring_sg_id
}

output "database_sg_id" {
  description = "ID of the database security group"
  value       = module.security.database_sg_id
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Zone ID of the Application Load Balancer"
  value       = aws_lb.main.zone_id
}

output "monitoring_instance_id" {
  description = "ID of the monitoring EC2 instance"
  value       = module.monitoring_compute.instance_id
}

output "monitoring_private_ip" {
  description = "Private IP of the monitoring instance"
  value       = module.monitoring_compute.private_ip
}

output "database_instance_id" {
  description = "ID of the database EC2 instance (if deployed)"
  value       = var.deploy_database ? module.database_compute[0].instance_id : null
}

output "database_private_ip" {
  description = "Private IP of the database instance (if deployed)"
  value       = var.deploy_database ? module.database_compute[0].private_ip : null
}

output "ssh_command_monitoring" {
  description = "SSH command to connect to monitoring instance"
  value       = "aws ssm start-session --target ${module.monitoring_compute.instance_id}"
}

output "ssh_command_database" {
  description = "SSH command to connect to database instance (if deployed)"
  value       = var.deploy_database ? "aws ssm start-session --target ${module.database_compute[0].instance_id}" : "Database not deployed"
}

output "grafana_url" {
  description = "URL to access Grafana"
  value       = "http://${aws_lb.main.dns_name}"
}

output "prometheus_url" {
  description = "URL to access Prometheus (via port-forward or direct)"
  value       = "Connect via: kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090"
}

output "postgresql_connection" {
  description = "PostgreSQL connection information"
  value = var.deploy_database ? {
    host             = module.database_compute[0].private_ip
    port             = "30432"
    database         = "appdb"
    username         = "postgres"
    password_command = "aws ssm get-parameter --name '${aws_ssm_parameter.postgres_password[0].name}' --with-decryption --query 'Parameter.Value' --output text"
    psql_command     = "psql -h ${module.database_compute[0].private_ip} -p 30432 -U postgres -d appdb"
  } : null
}

output "ssh_key_parameter_name" {
  description = "Parameter Store name for SSH private key"
  value       = var.key_pair_name == "" ? aws_ssm_parameter.private_key[0].name : "Using existing key pair: ${var.key_pair_name}"
}

output "grafana_password_parameter" {
  description = "Parameter Store name for Grafana admin password"
  value       = aws_ssm_parameter.grafana_password.name
  sensitive   = true
}

output "postgres_password_parameter" {
  description = "Parameter Store name for PostgreSQL password"
  value       = var.deploy_database ? aws_ssm_parameter.postgres_password[0].name : null
  sensitive   = true
}

output "deployment_summary" {
  description = "Summary of what was deployed"
  value = {
    monitoring_deployed = true
    database_deployed   = var.deploy_database
    lambda_deployed     = var.deploy_lambda && var.deploy_database
    region              = var.aws_region
    environment         = var.environment
    project_name        = var.project_name
  }
}

output "lambda_function_name" {
  description = "Name of the Lambda function (if deployed)"
  value       = var.deploy_lambda && var.deploy_database ? module.lambda[0].lambda_function_name : null
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function (if deployed)"
  value       = var.deploy_lambda && var.deploy_database ? module.lambda[0].lambda_function_arn : null
}

output "lambda_invoke_command" {
  description = "AWS CLI command to invoke the Lambda function"
  value       = var.deploy_lambda && var.deploy_database ? "aws lambda invoke --function-name ${module.lambda[0].lambda_function_name} --payload '{}' response.json && cat response.json" : "Lambda not deployed"
}

output "access_information" {
  description = "Complete access information for all services"
  value = {
    grafana = {
      url          = "http://${aws_lb.main.dns_name}"
      username     = "admin"
      password_cmd = "aws ssm get-parameter --name '${aws_ssm_parameter.grafana_password.name}' --with-decryption --query 'Parameter.Value' --output text"
    }
    prometheus = {
      method    = "SSH to monitoring instance, then:"
      command   = "kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090"
      local_url = "http://localhost:9090"
    }
    postgresql = var.deploy_database ? {
      host         = module.database_compute[0].private_ip
      port         = "30432"
      database     = "appdb"
      username     = "postgres"
      password_cmd = "aws ssm get-parameter --name '${aws_ssm_parameter.postgres_password[0].name}' --with-decryption --query 'Parameter.Value' --output text"
      psql_cmd     = "psql -h ${module.database_compute[0].private_ip} -p 30432 -U postgres -d appdb"
      note         = "Connect from monitoring instance or setup port forwarding"
      } : {
      status = "Not deployed"
      note   = "Set deploy_database=true to enable PostgreSQL"
    }
    ssh_access = {
      monitoring_instance = "aws ssm start-session --target ${module.monitoring_compute.instance_id}"
      database_instance   = var.deploy_database ? "aws ssm start-session --target ${module.database_compute[0].instance_id}" : "Not deployed"
    }
    lambda = var.deploy_lambda && var.deploy_database ? {
      function_name  = module.lambda[0].lambda_function_name
      function_arn   = module.lambda[0].lambda_function_arn
      invoke_command = "aws lambda invoke --function-name ${module.lambda[0].lambda_function_name} --payload '{}' response.json"
      logs_command   = "aws logs tail /aws/lambda/${module.lambda[0].lambda_function_name} --follow"
      note           = "Lambda can connect to database via VPC with secure Parameter Store access"
      } : {
      status = "Not deployed"
      note   = "Set deploy_lambda=true AND deploy_database=true to enable Lambda"
    }
    security_note = "Services are restricted to your IP. Update security groups if access issues occur."
  }
}
