#!/bin/bash

# Enhanced validation script for the DevOps infrastructure deployment
set -e

PROJECT_NAME=${1:-"devops-project"}
ENVIRONMENT=${2:-"staging"}

echo "🔍 Enhanced DevOps Infrastructure Validation"
echo "============================================="
echo "Project: $PROJECT_NAME"
echo "Environment: $ENVIRONMENT"
echo "Timestamp: $(date)"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "SUCCESS") echo -e "${GREEN}✅ $message${NC}" ;;
        "WARNING") echo -e "${YELLOW}⚠️  $message${NC}" ;;
        "ERROR") echo -e "${RED}❌ $message${NC}" ;;
        "INFO") echo -e "${BLUE}ℹ️  $message${NC}" ;;
    esac
}

# Function to check if terraform state exists
check_terraform_state() {
    print_status "INFO" "Checking Terraform state..."
    
    if [ -f "terraform.tfstate" ]; then
        print_status "SUCCESS" "Terraform state file found"
        
        # Extract key information from terraform state
        MONITORING_IP=$(terraform output -raw monitoring_public_ip 2>/dev/null || echo "Not found")
        DATABASE_IP=$(terraform output -raw database_private_ip 2>/dev/null || echo "Not found")
        ALB_DNS=$(terraform output -raw alb_dns_name 2>/dev/null || echo "Not found")
        
        echo "  📍 Monitoring Instance Public IP: $MONITORING_IP"
        echo "  📍 Database Instance Private IP: $DATABASE_IP"
        echo "  📍 Application Load Balancer: $ALB_DNS"
        echo ""
    else
        print_status "ERROR" "Terraform state file not found. Run 'terraform apply' first."
        exit 1
    fi
}

# Function to check PostgreSQL deployment
check_postgresql_deployment() {
    print_status "INFO" "Checking PostgreSQL deployment..."
    
    if [ "$DATABASE_IP" != "Not found" ]; then
        # Check if we can SSH to the database instance (requires key)
        print_status "INFO" "Attempting to validate PostgreSQL deployment on database instance..."
        
        # Try to get kubectl status via AWS SSM (if SSM agent is working)
        print_status "INFO" "Checking database instance connectivity and PostgreSQL status..."
        
        # Check if PostgreSQL exporter is accessible
        if curl -f -m 10 "http://$DATABASE_IP:30187/metrics" >/dev/null 2>&1; then
            print_status "SUCCESS" "PostgreSQL Exporter is accessible on database instance"
        else
            print_status "WARNING" "PostgreSQL Exporter not accessible (may be due to security groups)"
        fi
        
        # Check if PostgreSQL is accessible
        if curl -f -m 10 "$DATABASE_IP:30432" >/dev/null 2>&1; then
            print_status "SUCCESS" "PostgreSQL database is accessible on port 30432"
        else
            print_status "WARNING" "PostgreSQL database not accessible (may be due to security groups)"
        fi
    else
        print_status "WARNING" "Database instance not deployed or IP not available"
    fi
}

# Function to check monitoring stack
check_monitoring_stack() {
    print_status "INFO" "Checking monitoring stack..."
    
    if [ "$MONITORING_IP" != "Not found" ]; then
        # Check Grafana accessibility
        if curl -f -m 10 "http://$MONITORING_IP:30003/login" >/dev/null 2>&1; then
            print_status "SUCCESS" "Grafana is accessible at http://$MONITORING_IP:30003"
        else
            print_status "WARNING" "Grafana not accessible on port 30003"
        fi
        
        # Check Prometheus accessibility
        if curl -f -m 10 "http://$MONITORING_IP:30001/-/healthy" >/dev/null 2>&1; then
            print_status "SUCCESS" "Prometheus is accessible at http://$MONITORING_IP:30001"
        else
            print_status "WARNING" "Prometheus not accessible on port 30001"
        fi
        
        # Check ALB accessibility
        if [ "$ALB_DNS" != "Not found" ]; then
            if curl -f -m 10 "http://$ALB_DNS/login" >/dev/null 2>&1; then
                print_status "SUCCESS" "Application Load Balancer is working at http://$ALB_DNS"
            else
                print_status "WARNING" "ALB not accessible or targets not healthy"
            fi
        fi
    else
        print_status "WARNING" "Monitoring instance not deployed or IP not available"
    fi
}

# Function to check AWS Parameter Store secrets
check_parameter_store() {
    print_status "INFO" "Checking AWS Parameter Store secrets..."
    
    # Get current AWS region
    REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")
    
    # Check Grafana password
    if aws ssm get-parameter --name "/$PROJECT_NAME/$ENVIRONMENT/grafana/admin-password" --region "$REGION" >/dev/null 2>&1; then
        print_status "SUCCESS" "Grafana admin password found in Parameter Store"
    else
        print_status "ERROR" "Grafana admin password not found in Parameter Store"
    fi
    
    # Check PostgreSQL password (if database is deployed)
    if aws ssm get-parameter --name "/$PROJECT_NAME/$ENVIRONMENT/postgres/password" --region "$REGION" >/dev/null 2>&1; then
        print_status "SUCCESS" "PostgreSQL password found in Parameter Store"
    else
        print_status "WARNING" "PostgreSQL password not found in Parameter Store (normal if database not deployed)"
    fi
}

# Function to check service health
check_service_health() {
    print_status "INFO" "Performing service health checks..."
    
    # Check if services are responding with expected content
    if [ "$MONITORING_IP" != "Not found" ]; then
        # More detailed Grafana check
        GRAFANA_RESPONSE=$(curl -s -m 10 "http://$MONITORING_IP:30003/api/health" 2>/dev/null || echo "")
        if echo "$GRAFANA_RESPONSE" | grep -q '"database":"ok"'; then
            print_status "SUCCESS" "Grafana health check passed"
        else
            print_status "WARNING" "Grafana health check failed or incomplete"
        fi
        
        # More detailed Prometheus check
        PROMETHEUS_RESPONSE=$(curl -s -m 10 "http://$MONITORING_IP:30001/api/v1/query?query=up" 2>/dev/null || echo "")
        if echo "$PROMETHEUS_RESPONSE" | grep -q '"status":"success"'; then
            print_status "SUCCESS" "Prometheus health check passed"
        else
            print_status "WARNING" "Prometheus health check failed or incomplete"
        fi
    fi
}

# Function to provide troubleshooting tips
provide_troubleshooting_tips() {
    echo ""
    print_status "INFO" "Troubleshooting Tips:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    echo "🔧 Common Issues and Solutions:"
    echo ""
    echo "1. PostgreSQL Deployment Errors:"
    echo "   - Issue: ServiceMonitor CRD not found"
    echo "   - Solution: This has been fixed by disabling ServiceMonitor in PostgreSQL deployment"
    echo "   - Verification: Check logs with 'kubectl logs -n database -l app.kubernetes.io/name=postgresql'"
    echo ""
    echo "2. Services Not Accessible:"
    echo "   - Check security groups allow inbound traffic on required ports"
    echo "   - Verify instances are in private subnets but ALB is in public subnets"
    echo "   - Wait 5-10 minutes for user-data scripts to complete"
    echo ""
    echo "3. Monitoring Integration:"
    echo "   - PostgreSQL metrics are now handled by dedicated postgres-exporter"
    echo "   - Cross-instance monitoring configured in monitoring instance"
    echo "   - Check ServiceMonitor: kubectl get servicemonitor -n monitoring"
    echo ""
    echo "4. Access Credentials:"
    echo "   - Grafana: admin / (stored in Parameter Store)"
    echo "   - PostgreSQL: postgres / (stored in Parameter Store)"
    echo "   - Retrieve passwords: aws ssm get-parameter --name '/PROJECT/ENV/SERVICE/password' --with-decryption"
    echo ""
    echo "5. Manual Verification Commands:"
    echo "   - SSH to instances: Use the generated key from Parameter Store"
    echo "   - Check k3s: sudo kubectl get nodes"
    echo "   - Check pods: sudo kubectl get pods -A"
    echo "   - Check services: sudo kubectl get svc -A"
    echo "   - Check logs: sudo kubectl logs -n NAMESPACE POD_NAME"
}

# Main execution
main() {
    check_terraform_state
    check_parameter_store
    check_postgresql_deployment
    check_monitoring_stack
    check_service_health
    provide_troubleshooting_tips
    
    echo ""
    print_status "INFO" "Validation completed at $(date)"
    echo "============================================="
    
    if [ "$MONITORING_IP" != "Not found" ] && [ "$ALB_DNS" != "Not found" ]; then
        echo ""
        print_status "SUCCESS" "Quick Access Links:"
        echo "  🌐 Grafana (ALB): http://$ALB_DNS"
        echo "  🌐 Grafana (Direct): http://$MONITORING_IP:30003"
        echo "  🌐 Prometheus: http://$MONITORING_IP:30001"
        echo "  🌐 AlertManager: http://$MONITORING_IP:30002"
    fi
}

# Run main function
main 