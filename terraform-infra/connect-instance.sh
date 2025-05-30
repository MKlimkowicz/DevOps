#!/bin/bash

# Connect to Monitoring Instance Script
echo "🔗 Connecting to DevOps Portfolio Monitoring Instance"
echo "=================================================="

# Get instance ID from Terraform
INSTANCE_ID=$(terraform output -raw monitoring_instance_id 2>/dev/null)

if [ -z "$INSTANCE_ID" ]; then
    echo "❌ Could not get instance ID from Terraform outputs"
    echo "Make sure you're in the terraform directory and have applied the configuration"
    exit 1
fi

echo "📋 Instance ID: $INSTANCE_ID"

# Check instance status
echo "🔍 Checking instance status..."
INSTANCE_STATE=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null)

if [ "$INSTANCE_STATE" != "running" ]; then
    echo "❌ Instance is not running (State: $INSTANCE_STATE)"
    exit 1
fi

echo "✅ Instance is running"

# Check SSM connectivity with retry
echo "🔗 Attempting SSM connection..."
MAX_RETRIES=5
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if aws ssm start-session --target "$INSTANCE_ID" 2>/dev/null; then
        echo "✅ Connected successfully!"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "⏳ Attempt $RETRY_COUNT/$MAX_RETRIES failed. Retrying in 30 seconds..."
        
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "💡 SSM agent might still be initializing..."
            sleep 30
        fi
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ Failed to connect after $MAX_RETRIES attempts"
    echo ""
    echo "🛠️  Troubleshooting steps:"
    echo "  1. Wait 5-10 more minutes for SSM agent to fully initialize"
    echo "  2. Check SSM agent status:"
    echo "     aws ssm describe-instance-information --filters \"Key=InstanceIds,Values=$INSTANCE_ID\""
    echo "  3. Recreate instance with: terraform taint module.monitoring_compute.aws_instance.main && terraform apply"
    echo "  4. Check instance logs:"
    echo "     aws ec2 get-console-output --instance-id $INSTANCE_ID --output text | tail -50"
fi 