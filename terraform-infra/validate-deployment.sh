#!/bin/bash

# Deployment Validation Script
# This script validates that all components are working correctly

set -e

echo "🔍 DevOps Portfolio Infrastructure Validation"
echo "=============================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "ℹ️  $1"
}

# Get Terraform outputs
echo "📋 Getting Terraform outputs..."
MONITORING_INSTANCE_ID=$(terraform output -raw monitoring_instance_id 2>/dev/null || echo "")
ALB_DNS=$(terraform output -raw alb_dns_name 2>/dev/null || echo "")
GRAFANA_URL=$(terraform output -raw grafana_url 2>/dev/null || echo "")

if [ -z "$MONITORING_INSTANCE_ID" ]; then
    print_error "Could not get Terraform outputs. Make sure you're in the terraform directory and have applied the configuration."
    exit 1
fi

print_info "Monitoring Instance: $MONITORING_INSTANCE_ID"
print_info "ALB DNS: $ALB_DNS"
print_info "Grafana URL: $GRAFANA_URL"

# Check instance status
echo ""
echo "🖥️  Checking EC2 Instance Status..."
INSTANCE_STATE=$(aws ec2 describe-instances --instance-ids "$MONITORING_INSTANCE_ID" --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null || echo "error")

if [ "$INSTANCE_STATE" = "running" ]; then
    print_success "Instance is running"
else
    print_error "Instance is not running (State: $INSTANCE_STATE)"
    exit 1
fi

# Check instance status checks
echo ""
echo "🔍 Checking Instance Health..."
STATUS_CHECKS=$(aws ec2 describe-instance-status --instance-ids "$MONITORING_INSTANCE_ID" --query 'InstanceStatuses[0].InstanceStatus.Status' --output text 2>/dev/null || echo "error")
SYSTEM_CHECKS=$(aws ec2 describe-instance-status --instance-ids "$MONITORING_INSTANCE_ID" --query 'InstanceStatuses[0].SystemStatus.Status' --output text 2>/dev/null || echo "error")

if [ "$STATUS_CHECKS" = "ok" ]; then
    print_success "Instance status checks passed"
else
    print_warning "Instance status checks: $STATUS_CHECKS"
fi

if [ "$SYSTEM_CHECKS" = "ok" ]; then
    print_success "System status checks passed"
else
    print_warning "System status checks: $SYSTEM_CHECKS"
fi

# Check ALB target health
echo ""
echo "🎯 Checking ALB Target Health..."
TARGET_GROUP_ARN=$(aws elbv2 describe-target-groups --names devops-portfolio-dev-grafana --query 'TargetGroups[0].TargetGroupArn' --output text 2>/dev/null || echo "error")

if [ "$TARGET_GROUP_ARN" != "error" ]; then
    TARGET_HEALTH=$(aws elbv2 describe-target-health --target-group-arn "$TARGET_GROUP_ARN" --query 'TargetHealthDescriptions[0].TargetHealth.State' --output text 2>/dev/null || echo "error")
    
    if [ "$TARGET_HEALTH" = "healthy" ]; then
        print_success "ALB target is healthy"
    else
        print_warning "ALB target health: $TARGET_HEALTH"
    fi
else
    print_error "Could not retrieve target group information"
fi

# Test ALB connectivity
echo ""
echo "🌐 Testing ALB Connectivity..."
if [ -n "$GRAFANA_URL" ]; then
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$GRAFANA_URL" --max-time 10 2>/dev/null || echo "000")
    
    if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "302" ]; then
        print_success "ALB is responding (HTTP $HTTP_STATUS)"
    else
        print_warning "ALB response: HTTP $HTTP_STATUS"
    fi
else
    print_error "Grafana URL not available"
fi

# Check SSM connectivity
echo ""
echo "🔗 Testing SSM Connectivity..."
SSM_STATUS=$(aws ssm start-session --target "$MONITORING_INSTANCE_ID" --dry-run 2>&1 | grep -q "TargetNotConnected" && echo "not_connected" || echo "connected")

if [ "$SSM_STATUS" = "connected" ]; then
    print_success "SSM Session Manager is available"
else
    print_warning "SSM Session Manager not yet available (instance may still be booting)"
fi

# Get Grafana password
echo ""
echo "🔐 Checking Secrets..."
GRAFANA_PASSWORD_PARAM=$(terraform output -raw grafana_password_parameter 2>/dev/null || echo "")
if [ -n "$GRAFANA_PASSWORD_PARAM" ]; then
    GRAFANA_PASSWORD=$(aws ssm get-parameter --name "$GRAFANA_PASSWORD_PARAM" --with-decryption --query 'Parameter.Value' --output text 2>/dev/null || echo "error")
    
    if [ "$GRAFANA_PASSWORD" != "error" ] && [ -n "$GRAFANA_PASSWORD" ]; then
        print_success "Grafana password retrieved successfully"
        print_info "Grafana Password: $GRAFANA_PASSWORD"
    else
        print_error "Could not retrieve Grafana password"
    fi
else
    print_error "Grafana password parameter not found"
fi

echo ""
echo "📊 Validation Summary"
echo "===================="
print_info "Instance ID: $MONITORING_INSTANCE_ID"
print_info "Instance State: $INSTANCE_STATE"
print_info "Target Health: $TARGET_HEALTH"
print_info "HTTP Status: $HTTP_STATUS"
print_info "SSM Status: $SSM_STATUS"

echo ""
if [ "$INSTANCE_STATE" = "running" ] && [ "$TARGET_HEALTH" = "healthy" ] && ([ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "302" ]); then
    print_success "🎉 Deployment validation passed! Your infrastructure is ready."
    echo ""
    print_info "Next steps:"
    echo "  1. Open Grafana: $GRAFANA_URL"
    echo "  2. Login with username: admin"
    echo "  3. Use password: $GRAFANA_PASSWORD"
else
    print_warning "⏳ Deployment may still be in progress. Some services are not yet ready."
    echo ""
    print_info "Wait a few minutes and run this script again."
fi

echo ""
echo "🛠️  Troubleshooting commands:"
echo "  - View console logs: aws ec2 get-console-output --instance-id $MONITORING_INSTANCE_ID --output text"
echo "  - SSH to instance: aws ssm start-session --target $MONITORING_INSTANCE_ID"
echo "  - Check target health: aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN" 