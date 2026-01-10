resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-${var.environment}-infrastructure"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/EC2", "CPUUtilization", "InstanceId", var.monitoring_instance_id],
            var.database_instance_id != "" ? ["AWS/EC2", "CPUUtilization", "InstanceId", var.database_instance_id] : null
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "EC2 CPU Utilization"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/EC2", "NetworkIn", "InstanceId", var.monitoring_instance_id],
            ["AWS/EC2", "NetworkOut", "InstanceId", var.monitoring_instance_id],
            var.database_instance_id != "" ? ["AWS/EC2", "NetworkIn", "InstanceId", var.database_instance_id] : null,
            var.database_instance_id != "" ? ["AWS/EC2", "NetworkOut", "InstanceId", var.database_instance_id] : null
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Network Traffic"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/EC2", "StatusCheckFailed", "InstanceId", var.monitoring_instance_id],
            var.database_instance_id != "" ? ["AWS/EC2", "StatusCheckFailed", "InstanceId", var.database_instance_id] : null
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Status Checks"
          period  = 300
        }
      }
    ]
  })
}

data "aws_region" "current" {}

resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-${var.environment}-alerts"

  tags = {
    Name = "${var.project_name}-${var.environment}-alerts"
  }
}

resource "aws_cloudwatch_composite_alarm" "system_health" {
  alarm_name        = "${var.project_name}-${var.environment}-system-health"
  alarm_description = "Overall system health composite alarm"

  alarm_rule = join(" OR ", [
    "ALARM('${var.project_name}-${var.environment}-monitoring-high-cpu')",
    "ALARM('${var.project_name}-${var.environment}-monitoring-status-check')",
    var.deploy_database ? "ALARM('${var.project_name}-${var.environment}-database-high-cpu')" : "",
    var.deploy_database ? "ALARM('${var.project_name}-${var.environment}-database-status-check')" : ""
  ])

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]

  tags = {
    Name = "${var.project_name}-${var.environment}-system-health"
  }
}

resource "aws_cloudwatch_log_metric_filter" "error_count" {
  name           = "${var.project_name}-${var.environment}-error-count"
  log_group_name = "/aws/ec2/${var.project_name}-${var.environment}"
  pattern        = "[timestamp, request_id, \"ERROR\"]"

  metric_transformation {
    name      = "ErrorCount"
    namespace = "${var.project_name}/${var.environment}"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "application_errors" {
  alarm_name          = "${var.project_name}-${var.environment}-application-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ErrorCount"
  namespace           = "${var.project_name}/${var.environment}"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors application errors"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = {
    Name = "${var.project_name}-${var.environment}-application-errors"
  }
}
