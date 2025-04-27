resource "aws_security_group" "psql_sg" {
  name_prefix = "psql-sg-"
  description = "Security group for psql node exporter"
  vpc_id      = aws_vpc.this.id

  # Prometheus scrapes Node Exporter on the DB host
  ingress {
    from_port       = 9100
    to_port         = 9100
    protocol        = "tcp"
    security_groups = [aws_security_group.monitoring_sg.id]
  }

  # Outbound: HTTP/HTTPS for package installs, image pulls, etc.
  egress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "monitoring_sg" {
  name_prefix = "monitoring-sg-"
  description = "Security group for Prometheus & Grafana"
  vpc_id      = aws_vpc.this.id

  # ALB forwards to Prometheus
  ingress {
    from_port       = 9090
    to_port         = 9090
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  # ALB forwards to Grafana
  ingress {
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  # Outbound: allow internet for image pulls etc.
  egress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "alb_sg" {
  name_prefix = "alb-sg-"
  description = "ALB public SG"
  vpc_id      = aws_vpc.this.id

  # Public HTTPS access (locked down by variable)
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_alb_cidrs
  }

  # ALB needs egress to registered targets & health checks
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
