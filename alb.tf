resource "aws_lb" "public" {
  name               = "monitoring-alb"
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = [for s in aws_subnet.public : s.id]
  idle_timeout       = 60
  enable_deletion_protection = false
  tags = { Name = "monitoring-alb" }
}

resource "aws_lb_target_group" "prometheus" {
  name        = "tg-prometheus"
  port        = 9090
  protocol    = "HTTP"
  vpc_id      = aws_vpc.this.id
  target_type = "instance"
  health_check {
    path                = "/-/ready"
    port                = "9090"
    protocol            = "HTTP"
    matcher             = "200-399"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_target_group" "grafana" {
  name        = "tg-grafana"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.this.id
  target_type = "instance"
  health_check {
    path                = "/login"
    port                = "3000"
    protocol            = "HTTP"
    matcher             = "200-399"
  }
}

resource "aws_lb_target_group_attachment" "prometheus_attach" {
  target_group_arn = aws_lb_target_group.prometheus.arn
  target_id        = aws_instance.monitoring.id
  port             = 9090
}

resource "aws_lb_target_group_attachment" "grafana_attach" {
  target_group_arn = aws_lb_target_group.grafana.arn
  target_id        = aws_instance.monitoring.id
  port             = 3000
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.public.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.prometheus.arn
  }
}

resource "aws_lb_listener_rule" "grafana_route" {
  listener_arn = aws_lb_listener.http.arn  
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.grafana.arn
  }

  condition {
    path_pattern {
      values = ["/grafana/*", "/login"]
    }
  }
}