resource "aws_lambda_function" "database_connector" {
  function_name = "${var.project_name}-${var.environment}-db-connector"
  role          = var.lambda_role_arn

  filename         = "${path.module}/placeholder.zip"
  source_code_hash = data.archive_file.placeholder.output_base64sha256

  handler = "lambda_function.lambda_handler"
  runtime = "python3.11"
  timeout = 30

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [var.lambda_security_group_id]
  }

  environment {
    variables = {
      PROJECT_NAME = var.project_name
      ENVIRONMENT  = var.environment
      DB_HOST      = var.database_host
      DB_PORT      = "30432"
      DB_NAME      = "appdb"
      DB_USER      = "postgres"
      DB_PASSWORD_PARAM = "/${var.project_name}/${var.environment}/postgres/password"
    }
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-db-connector"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "Database connectivity for testing"
    Terraform   = "true"
  }
}

data "archive_file" "placeholder" {
  type        = "zip"
  output_path = "${path.module}/placeholder.zip"

  source {
    content  = <<EOF
import json
import boto3
import psycopg2
import os

def lambda_handler(event, context):
    """
    Placeholder Lambda function for database connectivity.
    This will be replaced with actual implementation.
    """
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Lambda function created successfully',
            'environment': os.environ.get('ENVIRONMENT'),
            'db_host': os.environ.get('DB_HOST')
        })
    }
EOF
    filename = "lambda_function.py"
  }
}

resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.database_connector.function_name}"
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-${var.environment}-lambda-logs"
  }

  lifecycle {
    create_before_destroy = true
  }
} 