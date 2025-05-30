#!/bin/bash

echo "🧹 CloudWatch Log Group Cleanup Script"
echo "This script helps clean up log groups before terraform destroy"

# Get project and environment from terraform outputs or variables
PROJECT_NAME=${1:-"devops-portfolio"}
ENVIRONMENT=${2:-"dev"}
REGION=${3:-"eu-central-1"}

echo "📋 Project: $PROJECT_NAME"
echo "📋 Environment: $ENVIRONMENT"
echo "📋 Region: $REGION"
echo ""

# List of log groups that might conflict
LOG_GROUPS=(
    "/aws/vpc/$PROJECT_NAME-$ENVIRONMENT-flow-logs"
    "/aws/ec2/$PROJECT_NAME-$ENVIRONMENT"
)

echo "🔍 Checking for existing log groups..."

for log_group in "${LOG_GROUPS[@]}"; do
    echo "Checking: $log_group"
    
    if aws logs describe-log-groups --log-group-name-prefix "$log_group" --region "$REGION" --query 'logGroups[0].logGroupName' --output text 2>/dev/null | grep -q "$log_group"; then
        echo "  ✅ Found: $log_group"
        
        read -p "  ❓ Delete $log_group? (y/n): " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "  🗑️  Deleting: $log_group"
            aws logs delete-log-group --log-group-name "$log_group" --region "$REGION"
            echo "  ✅ Deleted: $log_group"
        else
            echo "  ⏭️  Skipped: $log_group"
        fi
    else
        echo "  ➖ Not found: $log_group"
    fi
    echo ""
done

echo "🎉 Cleanup complete!"
echo ""
echo "💡 Usage tips:"
echo "   - Run this before 'terraform destroy' to avoid conflicts"
echo "   - Run this if you get ResourceAlreadyExistsException errors"
echo "   - Customize PROJECT_NAME and ENVIRONMENT as needed"
echo ""
echo "📚 Example usage:"
echo "   ./cleanup-logs.sh my-project prod eu-west-1" 