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
