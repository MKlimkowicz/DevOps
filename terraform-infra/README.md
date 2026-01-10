# DevOps Portfolio Infrastructure

Terraform infrastructure for deploying a monitoring and database stack on AWS using Kubernetes (k3s).

## Architecture

- EC2 instance with k3s running Grafana + Prometheus
- Optional EC2 instance with k3s running PostgreSQL
- Application Load Balancer for web access
- VPC with public/private subnets across 2 AZs
- CloudWatch integration

## Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform >= 1.0
- SSH key pair (optional - auto-generated if not provided)

## Quick Start

```bash
cd terraform-infra
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your IP address

terraform init
terraform apply -var="deploy_database=false"  # monitoring only
terraform apply -var="deploy_database=true"   # with database
```

## Project Structure

```
terraform-infra/
├── main.tf
├── variables.tf
├── outputs.tf
├── versions.tf
├── modules/
│   ├── vpc/
│   ├── security/
│   ├── compute/
│   └── monitoring/
└── configs/
    ├── prometheus/values.yaml
    ├── grafana/values.yaml
    └── postgresql/values.yaml
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `project_name` | Project identifier | `devops-portfolio` |
| `environment` | Environment name | `dev` |
| `deploy_database` | Deploy database instance | `false` |
| `aws_region` | AWS region | `us-west-2` |
| `instance_type` | EC2 instance type | `t3.medium` |
| `allowed_cidr_blocks` | CIDR blocks for ALB access | `["127.0.0.1/32"]` |
| `ssh_cidr_blocks` | CIDR blocks for SSH access | `["127.0.0.1/32"]` |

## Access

```bash
# Grafana URL
terraform output grafana_url

# Grafana password
aws ssm get-parameter --name "$(terraform output -raw grafana_password_parameter)" --with-decryption --query 'Parameter.Value' --output text

# PostgreSQL password
aws ssm get-parameter --name "$(terraform output -raw postgres_password_parameter)" --with-decryption --query 'Parameter.Value' --output text

# SSH to instances
aws ssm start-session --target $(terraform output -raw monitoring_instance_id)
```

## Service Endpoints

- **Grafana (ALB)**: `http://ALB_DNS`
- **Grafana (Direct)**: `http://MONITORING_IP:30003`
- **Prometheus**: `http://MONITORING_IP:30001`
- **AlertManager**: `http://MONITORING_IP:30002`
- **PostgreSQL**: `DATABASE_IP:30432`

## Troubleshooting

```bash
# Check instance status
aws ssm start-session --target INSTANCE_ID
sudo kubectl get nodes
sudo kubectl get pods -A
sudo tail -f /var/log/user-data.log

# Check PostgreSQL
kubectl get pods -n database
kubectl logs -n database -l app.kubernetes.io/name=postgresql

# Check Grafana
kubectl get pods -n monitoring -l app.kubernetes.io/name=grafana
```

## Tear-down

```bash
terraform destroy
```
