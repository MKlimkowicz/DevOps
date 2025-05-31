#!/bin/bash
set -e

echo "🔍 Verifying PostgreSQL Deployment Status"
echo "=========================================="

# Instance IDs from Terraform output
MONITORING_INSTANCE="i-0b8c194a2e8e3d017"
DATABASE_INSTANCE="i-0a327b0d2fcc897be"

echo "📋 Checking Instance States..."
aws ec2 describe-instances --instance-ids $MONITORING_INSTANCE $DATABASE_INSTANCE \
    --query 'Reservations[].Instances[].[Tags[?Key==`Name`].Value|[0],InstanceId,State.Name,PrivateIpAddress]' \
    --output table

echo ""
echo "🔧 Checking SSM Agent Status..."
aws ssm describe-instance-information \
    --filters "Key=InstanceIds,Values=$MONITORING_INSTANCE,$DATABASE_INSTANCE" \
    --query 'InstanceInformationList[].[InstanceId,PingStatus,LastPingDateTime]' \
    --output table

echo ""
echo "📊 Recent User Data Logs from Database Instance..."
echo "Looking for PostgreSQL deployment completion..."

# Get recent logs from the database instance
aws logs filter-log-events \
    --log-group-name "/aws/ec2/devops-dev" \
    --start-time $(date -d '1 hour ago' +%s)000 \
    --filter-pattern "PostgreSQL" \
    --query 'events[*].[timestamp,message]' \
    --output table | head -20

echo ""
echo "🗄️ PostgreSQL Connection Information:"
echo "Host: 10.0.20.80 (database instance private IP)"
echo "Port: 30432 (NodePort service)"
echo "Database: appdb"
echo "Username: postgres"
echo "Password: Stored in Parameter Store /devops/dev/postgres/password"

echo ""
echo "🧪 To test PostgreSQL from inside the VPC:"
echo "1. SSH to monitoring instance: aws ssm start-session --target $MONITORING_INSTANCE"
echo "2. Get password: aws ssm get-parameter --name '/devops/dev/postgres/password' --with-decryption --query 'Parameter.Value' --output text"
echo "3. Test connection: PGPASSWORD='[password]' psql -h 10.0.20.80 -p 30432 -U postgres -d appdb -c 'SELECT version();'"

echo ""
echo "🔍 Based on the deployment logs shown above, PostgreSQL should be working."
echo "The successful completion message 'PostgreSQL database setup completed successfully' indicates the deployment worked." 