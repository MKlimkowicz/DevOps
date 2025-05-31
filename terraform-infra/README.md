# DevOps Portfolio Infrastructure

A production-ready Terraform infrastructure for deploying a comprehensive monitoring and database stack on AWS using Kubernetes (k3s).

## 🏗️ Architecture Overview

This infrastructure deploys:

- **Always**: EC2 instance with Kubernetes (k3s) running Grafana + Prometheus monitoring stack
- **Optional**: EC2 instance with Kubernetes (k3s) running PostgreSQL database
- **Load Balancer**: Application Load Balancer for web interface access
- **Networking**: Custom VPC with public/private subnets across 2 AZs
- **Security**: Least privilege security groups and IAM roles
- **Monitoring**: CloudWatch integration and custom dashboards

## 📋 Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform >= 1.0 installed
- SSH key pair (optional - will be auto-generated if not provided)

## 🚀 Quick Start

### 1. Clone and Configure

```bash
cd terraform-infra
```

### 2. **IMPORTANT: Set Your IP Address (Required for Security)**

**Option A: Automated Setup (Recommended)**
```bash
# Run the automated setup script
./setup-security.sh
```

**Option B: Manual Setup**
```bash
# Get your public IP
curl ifconfig.me

# Copy and edit configuration
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars

# Update these lines with your actual IP:
# allowed_cidr_blocks = ["YOUR_ACTUAL_IP/32"]
# ssh_cidr_blocks     = ["YOUR_ACTUAL_IP/32"]
```

### 3. Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Plan deployment (monitoring only)
terraform plan -var="deploy_database=false"

# Deploy monitoring stack
terraform apply -var="deploy_database=false"

# Or deploy with database
terraform apply -var="deploy_database=true"
```

### 4. Access Services

After deployment, get the access URLs:

```bash
# Get Grafana URL
terraform output grafana_url

# Get admin password
aws ssm get-parameter --name "$(terraform output grafana_password_parameter)" --with-decryption --query 'Parameter.Value' --output text
```

## 📁 Project Structure

```
terraform-infra/
├── main.tf                    # Main Terraform configuration
├── variables.tf               # Variable definitions
├── outputs.tf                 # Output definitions
├── versions.tf                # Provider versions
├── terraform.tfvars.example  # Example variables file
├── modules/
│   ├── vpc/                   # VPC, subnets, gateways
│   ├── security/              # Security groups, IAM roles
│   ├── compute/               # EC2 instances, EBS volumes
│   └── monitoring/            # CloudWatch dashboards, alarms
├── scripts/
│   ├── user-data-template.sh  # EC2 initialization template
│   ├── install-k3s.sh         # Kubernetes installation
│   ├── setup-monitoring.sh    # Prometheus/Grafana setup
│   ├── setup-database.sh      # PostgreSQL setup
│   └── configure-prometheus.sh # Prometheus configuration
├── configs/
│   ├── prometheus/values.yaml # Prometheus Helm values
│   ├── grafana/values.yaml    # Grafana Helm values
│   └── postgresql/values.yaml # PostgreSQL Helm values
└── README.md
```

## 🔧 Configuration Options

### Core Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `project_name` | Project identifier | `devops-portfolio` | No |
| `environment` | Environment name | `dev` | No |
| `deploy_database` | Deploy database instance | `false` | No |
| `aws_region` | AWS region | `us-west-2` | No |
| `instance_type` | EC2 instance type | `t3.medium` | No |

### Security Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `allowed_cidr_blocks` | CIDR blocks for ALB access | `["0.0.0.0/0"]` | No |
| `ssh_cidr_blocks` | CIDR blocks for SSH access | `["0.0.0.0/0"]` | No |
| `key_pair_name` | Existing SSH key pair | `""` (auto-generate) | No |

### Network Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `vpc_cidr` | VPC CIDR block | `10.0.0.0/16` | No |
| `public_subnet_cidrs` | Public subnet CIDRs | `["10.0.1.0/24", "10.0.2.0/24"]` | No |
| `private_subnet_cidrs` | Private subnet CIDRs | `["10.0.10.0/24", "10.0.20.0/24"]` | No |

## 🔐 Security Features

### Network Security
- **VPC Isolation**: Custom VPC with private subnets for EC2 instances
- **Security Groups**: Least privilege access rules
- **NAT Gateway**: Secure internet access for private instances
- **Secure Defaults**: ✅ **NEW** - Default configuration now requires explicit IP specification

### Secure by Default Configuration
- **ALB Access**: Restricted to your IP only (no more 0.0.0.0/0)
- **SSH Access**: Restricted to your IP only
- **PostgreSQL**: Direct access via private IP with authentication
- **Auto-generated Secrets**: Grafana and PostgreSQL passwords stored securely

### Access Control
- **IAM Roles**: Minimal required permissions for EC2 instances
- **SSH Keys**: Key-based authentication only
- **Parameter Store**: Secure storage for passwords and keys

### Data Protection
- **EBS Encryption**: All volumes encrypted at rest
- **TLS**: HTTPS/TLS for all web interfaces
- **Secrets Management**: AWS Systems Manager Parameter Store

### How to Get Your IP
```bash
# Multiple ways to get your public IP:
curl ifconfig.me
curl icanhazip.com
curl ipinfo.io/ip
```

## 📊 Service Access After Deployment

After running `terraform apply`, you'll see a complete access summary. Here's how to connect:

### 🌐 Grafana Access
```bash
# 1. Get the URL from terraform output
terraform output -json access_information

# 2. Get the admin password
aws ssm get-parameter --name "$(terraform output -raw grafana_password_parameter)" --with-decryption --query 'Parameter.Value' --output text

# 3. Open browser to the ALB URL
# Username: admin
# Password: (from step 2)
```

### 🗄️ PostgreSQL Access
```bash
# 1. Get connection details
terraform output -json postgresql_connection

# 2. Get the password
PGPASSWORD=$(aws ssm get-parameter --name "$(terraform output -raw postgres_password_parameter)" --with-decryption --query 'Parameter.Value' --output text)

# 3. Connect directly via private IP (from monitoring instance or VPN)
psql -h $(terraform output -raw monitoring_private_ip) -p 30432 -U postgres -d appdb

# Alternative: SSH to monitoring instance first
aws ssm start-session --target $(terraform output -raw monitoring_instance_id)
# Then from inside: psql -h localhost -p 30432 -U postgres -d appdb
```

### 📊 Prometheus Access
```bash
# SSH to monitoring instance
aws ssm start-session --target $(terraform output -raw monitoring_instance_id)

# Port forward Prometheus
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090

# Access via http://localhost:9090
```

## 📊 Monitoring & Observability

### Included Dashboards
- **Infrastructure Overview**: CPU, memory, disk, network metrics
- **Kubernetes Cluster**: Pod status, resource usage
- **PostgreSQL**: Database performance and health (when deployed)

### Alerting Rules
- High CPU usage (>80% for 5 minutes)
- High memory usage (>85% for 5 minutes)
- Low disk space (>90% usage)
- PostgreSQL down (when deployed)

### Log Aggregation
- CloudWatch Logs integration
- Application and system logs
- Centralized log management

## 🗄️ Database Features (Optional)

When `deploy_database = true`:

- **PostgreSQL 15**: Production-ready database
- **Persistent Storage**: 10GB encrypted EBS volume
- **Monitoring**: Prometheus metrics and Grafana dashboards
- **Backup**: Automated EBS snapshots
- **Sample Data**: Pre-loaded with example tables

### Database Access

```bash
# Get database password
aws ssm get-parameter --name "$(terraform output postgres_password_parameter)" --with-decryption --query 'Parameter.Value' --output text

# Connect via kubectl port-forward
kubectl port-forward -n database svc/postgresql 5432:5432

# Connect with psql
psql -h localhost -p 5432 -U postgres -d appdb
```

## 🔄 Deployment Scenarios

### Scenario 1: Monitoring Only
```bash
terraform apply -var="deploy_database=false"
```
- Deploys: 1 EC2 instance with monitoring stack
- Cost: ~$25-30/month
- Use case: Basic infrastructure monitoring

### Scenario 2: Full Stack
```bash
terraform apply -var="deploy_database=true"
```
- Deploys: 2 EC2 instances (monitoring + database)
- Cost: ~$50-60/month
- Use case: Complete application stack with database

### Scenario 3: Production Setup
```bash
terraform apply \
  -var="deploy_database=true" \
  -var="instance_type=t3.large" \
  -var="allowed_cidr_blocks=[\"YOUR_OFFICE_IP/32\"]" \
  -var="ssh_cidr_blocks=[\"YOUR_OFFICE_IP/32\"]"
```

## 🛠️ Maintenance

### Updating Infrastructure
```bash
# Update Terraform modules
terraform get -update

# Plan changes
terraform plan

# Apply updates
terraform apply
```

### Scaling Resources
```bash
# Scale to larger instances
terraform apply -var="instance_type=t3.large"

# Increase storage
terraform apply -var="ebs_volume_size=50"
```

### Backup and Recovery
- **EBS Snapshots**: Automated daily snapshots (7-day retention)
- **Configuration Backup**: Terraform state in S3 (recommended)
- **Application Data**: Database dumps via cron jobs

## 🔍 Troubleshooting

### Common Issues

1. **Instance not accessible**
   ```bash
   # Check security groups
   aws ec2 describe-security-groups --group-ids $(terraform output monitoring_sg_id)
   
   # Use SSM Session Manager
   aws ssm start-session --target $(terraform output monitoring_instance_id)
   ```

2. **CloudWatch Log Group Already Exists**
   ```bash
   # Use the cleanup script before destroy/recreate
   ./cleanup-logs.sh
   
   # Or manually delete specific log groups
   aws logs delete-log-group --log-group-name "/aws/vpc/devops-portfolio-dev-flow-logs" --region eu-central-1
   ```

3. **Services not starting**
   ```bash
   # Check user-data logs
   aws ssm start-session --target $(terraform output monitoring_instance_id)
   sudo tail -f /var/log/user-data.log
   ```

4. **Database connection issues**
   ```bash
   # Check PostgreSQL status
   kubectl get pods -n database
   kubectl logs -n database deployment/postgresql
   ```

### Log Group Management

**Problem**: CloudWatch log groups persist after `terraform destroy` and cause conflicts on recreation.

**Solution**: Use the provided cleanup script:
```bash
# Before destroying infrastructure
./cleanup-logs.sh

# Or specify custom parameters
./cleanup-logs.sh my-project prod eu-west-1
```

**Why this happens**: CloudWatch log groups are not always deleted when referenced resources are destroyed, leading to `ResourceAlreadyExistsException` errors.

**Prevention**: The infrastructure now includes:
- `create_before_destroy = true` lifecycle rules
- `ignore_changes` for log group names
- Automated cleanup script for manual intervention

### Useful Commands

```bash
# Get all outputs
terraform output

# SSH to instances (via SSM)
aws ssm start-session --target $(terraform output monitoring_instance_id)

# Check Kubernetes status
kubectl get nodes
kubectl get pods --all-namespaces

# View Grafana password
aws ssm get-parameter --name "$(terraform output grafana_password_parameter)" --with-decryption --query 'Parameter.Value' --output text
```

## 💰 Cost Optimization

### Cost Breakdown (us-west-2)
- **t3.medium instances**: ~$24/month each
- **EBS volumes (20GB gp3)**: ~$2/month each
- **NAT Gateway**: ~$32/month
- **ALB**: ~$16/month
- **Data transfer**: Variable

### Cost Saving Tips
1. **Use Spot Instances**: Add spot instance configuration
2. **Schedule Instances**: Stop instances during off-hours
3. **Optimize Storage**: Use gp3 instead of gp2
4. **Monitor Usage**: Set up billing alerts

## 🚨 Production Considerations

### Security Hardening
- [ ] Restrict CIDR blocks to known IPs
- [ ] Enable VPC Flow Logs
- [ ] Implement WAF for ALB
- [ ] Use AWS Secrets Manager for sensitive data
- [ ] Enable GuardDuty for threat detection

### High Availability
- [ ] Deploy across multiple AZs
- [ ] Implement Auto Scaling Groups
- [ ] Use RDS for production database
- [ ] Set up cross-region backups

### Monitoring Enhancements
- [ ] Set up SNS notifications for alerts
- [ ] Implement log aggregation with ELK stack
- [ ] Add custom application metrics
- [ ] Configure Slack/email alerting

## 📚 Additional Resources

- [Terraform AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [k3s Documentation](https://k3s.io/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**⚠️ Important**: This infrastructure creates AWS resources that incur costs. Always run `terraform destroy` when you're done testing to avoid unexpected charges.

## Recent Fixes (PostgreSQL Deployment)

### 🔧 **Issue Resolved: ServiceMonitor CRD Error**

**Problem**: PostgreSQL deployment was failing with:
```
Error: unable to build kubernetes objects from release manifest: resource mapping not found for name: "postgresql" namespace: "monitoring" from "": no matches for kind "ServiceMonitor" in version "monitoring.coreos.com/v1"
```

**Root Cause**: 
- PostgreSQL was trying to create ServiceMonitor CRDs before Prometheus Operator was installed
- Configuration conflicts between different deployment scripts
- Script execution order dependency issues

**Solution Implemented**:
1. **Disabled ServiceMonitor in PostgreSQL deployment** to eliminate CRD dependencies
2. **Centralized monitoring** - all ServiceMonitors are now created on the monitoring instance
3. **Fixed configuration conflicts** across all deployment scripts
4. **Enhanced cross-instance monitoring** with proper error handling and validation

**Key Changes**:
- `setup-database.sh`: Disabled metrics and ServiceMonitor components
- `user-data-template.sh`: Fixed embedded PostgreSQL script
- `configs/postgresql/values.yaml`: Updated to disable monitoring components
- `setup-monitoring.sh`: Enhanced with better error handling and validation
- `validate-deployment.sh`: Added comprehensive troubleshooting tools

## Quick Start

1. **Configure Variables**:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your settings
   ```

2. **Deploy Infrastructure**:
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

3. **Validate Deployment**:
   ```bash
   ./validate-deployment.sh your-project-name your-environment
   ```

## Troubleshooting

### PostgreSQL Issues

**ServiceMonitor Errors**: ✅ **RESOLVED**
- ServiceMonitor is now disabled in PostgreSQL deployment
- Monitoring is handled centrally from the monitoring instance

**Database Connection Issues**:
```bash
# Check PostgreSQL status
kubectl get pods -n database
kubectl logs -n database -l app.kubernetes.io/name=postgresql

# Test database connectivity
kubectl exec -n database deployment/postgresql -- psql -U postgres -d appdb -c "SELECT version();"
```

**Postgres Exporter Issues**:
```bash
# Check exporter status
kubectl get pods -n database -l app=postgres-exporter
kubectl logs -n database -l app=postgres-exporter

# Test metrics endpoint
curl http://DATABASE_IP:30187/metrics
```

### Monitoring Issues

**Grafana Not Accessible**:
```bash
# Check Grafana status
kubectl get pods -n monitoring -l app.kubernetes.io/name=grafana

# Check service
kubectl get svc -n monitoring grafana-alb

# Check ALB target health
aws elbv2 describe-target-health --target-group-arn TARGET_GROUP_ARN
```

**Missing PostgreSQL Metrics**:
```bash
# Check ServiceMonitor
kubectl get servicemonitor -n monitoring postgres-external

# Check if monitoring instance can reach database
curl http://DATABASE_IP:30187/metrics

# Check Prometheus targets
# Go to http://MONITORING_IP:30001/targets
```

### Common Commands

**Get Passwords**:
```bash
# Grafana admin password
aws ssm get-parameter --name "/PROJECT/ENV/grafana/admin-password" --with-decryption --query 'Parameter.Value' --output text

# PostgreSQL password
aws ssm get-parameter --name "/PROJECT/ENV/postgres/password" --with-decryption --query 'Parameter.Value' --output text
```

**Check Instance Status**:
```bash
# SSH to instances
aws ssm start-session --target INSTANCE_ID

# Check k3s status
sudo kubectl get nodes
sudo kubectl get pods -A

# Check user-data logs
sudo tail -f /var/log/user-data.log
```

**Network Troubleshooting**:
```bash
# Test connectivity between instances
curl -f http://INSTANCE_IP:PORT

# Check security groups
aws ec2 describe-security-groups --group-ids sg-xxxxx

# Check ALB health
curl -f http://ALB_DNS/login
```

## Access Information

After successful deployment:

- **Grafana (via ALB)**: `http://ALB_DNS`
- **Grafana (Direct)**: `http://MONITORING_IP:30003`
- **Prometheus**: `http://MONITORING_IP:30001`
- **AlertManager**: `http://MONITORING_IP:30002`
- **PostgreSQL**: `DATABASE_IP:30432` (internal access only)

**Default Credentials**:
- Grafana: `admin` / (get from Parameter Store)
- PostgreSQL: `postgres` / (get from Parameter Store)

## Monitoring Features

- **Infrastructure Monitoring**: CPU, Memory, Disk usage
- **PostgreSQL Monitoring**: Database metrics, connections, query performance
- **Cross-Instance Monitoring**: Centralized monitoring of distributed components
- **Custom Dashboards**: Pre-configured dashboards for PostgreSQL and infrastructure
- **Alerting**: Configured alerts for high resource usage and database issues

## Architecture Decisions

1. **Separated Database and Monitoring**: Improved resource isolation and scalability
2. **Disabled Built-in ServiceMonitors**: Eliminates CRD dependency issues
3. **Centralized Monitoring**: All monitoring configuration managed from monitoring instance
4. **NodePort Services**: Enables cross-instance communication in private subnets
5. **Parameter Store Integration**: Secure credential management

## Contributing

When making changes to deployment scripts:

1. Test changes in a separate environment first
2. Update validation scripts accordingly
3. Document any new troubleshooting steps
4. Ensure backward compatibility

## Support

For issues related to:
- **PostgreSQL Deployment**: Check the troubleshooting section above
- **Monitoring Setup**: Use the validation script for diagnostics
- **Network Connectivity**: Verify security groups and instance status
- **Access Issues**: Ensure credentials are retrieved from Parameter Store

Run `./validate-deployment.sh` for comprehensive health checks and troubleshooting guidance.
