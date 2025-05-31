# Lambda Database Connector Module

This module creates an AWS Lambda function that can securely connect to the PostgreSQL database deployed in the DevOps infrastructure.

## Features

- **VPC Integration**: Lambda runs in private subnets with secure database access
- **Parameter Store Integration**: Securely retrieves database credentials from AWS Systems Manager
- **CloudWatch Logging**: Comprehensive logging for debugging and monitoring
- **Security Groups**: Restrictive network access following principle of least privilege

## Architecture

```
Lambda Function (Private Subnet)
    ↓
VPC Endpoints (SSM, Logs)
    ↓
Security Groups
    ↓
PostgreSQL Database (Private Subnet, Port 30432)
```

## Security Features

1. **Network Isolation**: Lambda runs in private subnets with no internet access
2. **VPC Endpoints**: AWS service access via private endpoints (SSM, CloudWatch Logs)
3. **Security Groups**: Specific rules allowing only Lambda → Database connectivity
4. **IAM Roles**: Minimal permissions for Parameter Store and CloudWatch access
5. **Encrypted Secrets**: Database password stored securely in Parameter Store

## Configuration

The Lambda function is configured with environment variables:
- `PROJECT_NAME`: Project identifier
- `ENVIRONMENT`: Environment (dev/staging/prod)
- `DB_HOST`: Database host IP address
- `DB_PORT`: Database port (30432)
- `DB_NAME`: Database name (appdb)
- `DB_USER`: Database username (postgres)
- `DB_PASSWORD_PARAM`: Parameter Store path for password

## Usage

To enable Lambda deployment:

1. Set `deploy_database = true` in terraform.tfvars
2. Set `deploy_lambda = true` in terraform.tfvars
3. Apply Terraform configuration

## Testing Connectivity

After deployment, test the Lambda function:

```bash
# Invoke the function
aws lambda invoke --function-name <function-name> --payload '{}' response.json

# View the response
cat response.json

# Check logs
aws logs tail /aws/lambda/<function-name> --follow
```

## Python Dependencies

The Lambda function supports the following Python packages:
- `psycopg2-binary`: PostgreSQL adapter
- `boto3`: AWS SDK (included in Lambda runtime)

## Notes

- Lambda requires both database and Lambda deployment flags to be enabled
- The function is created with a placeholder implementation
- VPC configuration may result in longer cold start times
- Ensure sufficient subnet IP addresses for Lambda ENIs 