data "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-${var.environment}-ec2-profile"
}

locals {
  user_data = base64encode(<<-EOT
    set -e
    
    exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
    echo "Starting minimal user data script for ${var.instance_name} instance at $(date)"
    
    dnf update -y
    
    dnf install -y amazon-ssm-agent awscli
    
    systemctl enable amazon-ssm-agent
    systemctl start amazon-ssm-agent
    
    mkdir -p /opt/ansible-setup
    chown ec2-user:ec2-user /opt/ansible-setup
    
    echo "Basic setup completed at $(date). Ansible will handle additional configuration."
    EOT
  )
}

resource "aws_instance" "main" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  key_name               = var.key_name
  subnet_id              = var.subnet_id
  vpc_security_group_ids = var.vpc_security_group_ids
  iam_instance_profile   = data.aws_iam_instance_profile.ec2_profile.name

  user_data = local.user_data

  monitoring = var.enable_detailed_monitoring

  root_block_device {
    volume_type           = var.ebs_volume_type
    volume_size           = var.ebs_volume_size
    encrypted             = true
    delete_on_termination = true

    tags = {
      Name = "${var.project_name}-${var.environment}-${var.instance_name}-root"
    }
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-${var.instance_name}"
    Type = var.instance_name
  }

  lifecycle {
    create_before_destroy = false
  }
}

resource "aws_ebs_volume" "app_data" {
  availability_zone = aws_instance.main.availability_zone
  size              = var.ebs_volume_size
  type              = var.ebs_volume_type
  encrypted         = true

  tags = {
    Name = "${var.project_name}-${var.environment}-${var.instance_name}-data"
  }
}

resource "aws_volume_attachment" "app_data" {
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.app_data.id
  instance_id = aws_instance.main.id
}

resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "${var.project_name}-${var.environment}-${var.instance_name}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ec2 cpu utilization"

  dimensions = {
    InstanceId = aws_instance.main.id
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-${var.instance_name}-cpu-alarm"
  }
}

resource "aws_cloudwatch_metric_alarm" "status_check" {
  alarm_name          = "${var.project_name}-${var.environment}-${var.instance_name}-status-check"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Maximum"
  threshold           = "0"
  alarm_description   = "This metric monitors ec2 status check"

  dimensions = {
    InstanceId = aws_instance.main.id
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-${var.instance_name}-status-alarm"
  }
}
