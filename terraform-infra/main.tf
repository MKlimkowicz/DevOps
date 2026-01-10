data "aws_caller_identity" "current" {}

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "state"
    values = ["available"]
  }
}

resource "random_password" "grafana_password" {
  count   = var.grafana_admin_password == "" ? 1 : 0
  length  = 16
  special = true
}

resource "random_password" "postgres_password" {
  count   = var.postgres_password == "" ? 1 : 0
  length  = 16
  special = true
}

resource "aws_ssm_parameter" "grafana_password" {
  name  = "/${var.project_name}/${var.environment}/grafana/admin-password"
  type  = "SecureString"
  value = var.grafana_admin_password != "" ? var.grafana_admin_password : random_password.grafana_password[0].result

  tags = {
    Name = "${var.project_name}-grafana-password"
  }
}

resource "aws_ssm_parameter" "postgres_password" {
  count = var.deploy_database ? 1 : 0
  name  = "/${var.project_name}/${var.environment}/postgres/password"
  type  = "SecureString"
  value = random_password.postgres_password[0].result

  tags = {
    Name = "${var.project_name}-postgres-password"
  }
}

resource "aws_ssm_parameter" "database_private_ip" {
  count = var.deploy_database ? 1 : 0
  name  = "/${var.project_name}/${var.environment}/database/private-ip"
  type  = "String"
  value = module.database_compute[0].private_ip

  tags = {
    Name = "${var.project_name}-database-private-ip"
  }
}

resource "tls_private_key" "ec2_key" {
  count     = var.key_pair_name == "" ? 1 : 0
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "ec2_key" {
  count      = var.key_pair_name == "" ? 1 : 0
  key_name   = "${var.project_name}-${var.environment}-key"
  public_key = tls_private_key.ec2_key[0].public_key_openssh

  tags = {
    Name = "${var.project_name}-${var.environment}-key"
  }
}

resource "aws_ssm_parameter" "private_key" {
  count = var.key_pair_name == "" ? 1 : 0
  name  = "/${var.project_name}/${var.environment}/ssh/private-key"
  type  = "SecureString"
  value = tls_private_key.ec2_key[0].private_key_pem

  tags = {
    Name = "${var.project_name}-ssh-private-key"
  }
}

module "vpc" {
  source = "./modules/vpc"

  project_name         = var.project_name
  environment          = var.environment
  vpc_cidr             = var.vpc_cidr
  availability_zones   = var.availability_zones
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
}

module "security" {
  source = "./modules/security"

  project_name        = var.project_name
  environment         = var.environment
  vpc_id              = module.vpc.vpc_id
  allowed_cidr_blocks = var.allowed_cidr_blocks
  ssh_cidr_blocks     = var.ssh_cidr_blocks
}

module "monitoring_compute" {
  source = "./modules/compute"

  project_name               = var.project_name
  environment                = var.environment
  instance_name              = "monitoring"
  ami_id                     = data.aws_ami.amazon_linux.id
  instance_type              = var.instance_type
  key_name                   = var.key_pair_name != "" ? var.key_pair_name : aws_key_pair.ec2_key[0].key_name
  subnet_id                  = module.vpc.private_subnet_ids[0]
  vpc_security_group_ids     = [module.security.monitoring_sg_id]
  ebs_volume_size            = var.ebs_volume_size
  ebs_volume_type            = var.ebs_volume_type
  enable_detailed_monitoring = var.enable_detailed_monitoring
  deploy_database            = var.deploy_database

  depends_on = [module.vpc, module.security]
}

module "database_compute" {
  count  = var.deploy_database ? 1 : 0
  source = "./modules/compute"

  project_name               = var.project_name
  environment                = var.environment
  instance_name              = "database"
  ami_id                     = data.aws_ami.amazon_linux.id
  instance_type              = var.instance_type
  key_name                   = var.key_pair_name != "" ? var.key_pair_name : aws_key_pair.ec2_key[0].key_name
  subnet_id                  = module.vpc.private_subnet_ids[1]
  vpc_security_group_ids     = [module.security.database_sg_id]
  ebs_volume_size            = var.ebs_volume_size
  ebs_volume_type            = var.ebs_volume_type
  enable_detailed_monitoring = var.enable_detailed_monitoring
  deploy_database            = var.deploy_database

  depends_on = [module.vpc, module.security]
}

module "lambda" {
  count  = var.deploy_lambda && var.deploy_database ? 1 : 0
  source = "./modules/lambda"

  project_name             = var.project_name
  environment              = var.environment
  lambda_role_arn          = module.security.lambda_role_arn
  private_subnet_ids       = module.vpc.private_subnet_ids
  lambda_security_group_id = module.security.lambda_sg_id
  database_host            = module.database_compute[0].private_ip

  depends_on = [module.vpc, module.security, module.database_compute]
}

resource "aws_lb" "main" {
  name               = "${var.project_name}-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [module.security.alb_sg_id]
  subnets            = module.vpc.public_subnet_ids

  enable_deletion_protection = false

  tags = {
    Name        = "${var.project_name}-${var.environment}-alb"
    Project     = var.project_name
    Environment = var.environment
    Owner       = var.owner
    Purpose     = "Application Load Balancer for Grafana/Prometheus"
    Terraform   = "true"
  }
}

resource "aws_lb_target_group" "grafana" {
  name     = "${var.project_name}-${var.environment}-grafana"
  port     = 30003
  protocol = "HTTP"
  vpc_id   = module.vpc.vpc_id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 10
    interval            = 30
    path                = "/login"
    matcher             = "200,302"
    port                = "traffic-port"
    protocol            = "HTTP"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-grafana-tg"
    Project     = var.project_name
    Environment = var.environment
    Owner       = var.owner
    Purpose     = "Target group for Grafana service"
    Terraform   = "true"
  }
}

resource "aws_lb_target_group_attachment" "grafana" {
  target_group_arn = aws_lb_target_group.grafana.arn
  target_id        = module.monitoring_compute.instance_id
  port             = 30003
}

resource "aws_lb_listener" "web" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.grafana.arn
  }
}

resource "aws_cloudwatch_log_group" "application" {
  name              = "/aws/ec2/${var.project_name}-${var.environment}"
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-${var.environment}-log-group"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_dlm_lifecycle_policy" "ebs_snapshot" {
  description        = "EBS snapshot policy for ${var.project_name}"
  execution_role_arn = aws_iam_role.dlm_lifecycle_role.arn
  state              = "ENABLED"

  policy_details {
    resource_types = ["VOLUME"]
    target_tags = {
      Project = var.project_name
    }

    schedule {
      name = "Daily snapshots"

      create_rule {
        interval      = 24
        interval_unit = "HOURS"
        times         = ["03:00"]
      }

      retain_rule {
        count = 7
      }

      copy_tags = true
    }
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-snapshot-policy"
  }
}

resource "aws_iam_role" "dlm_lifecycle_role" {
  name = "${var.project_name}-${var.environment}-dlm-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "dlm.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-dlm-role"
  }
}

resource "aws_iam_role_policy_attachment" "dlm_lifecycle_policy" {
  role       = aws_iam_role.dlm_lifecycle_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSDataLifecycleManagerServiceRole"
}
