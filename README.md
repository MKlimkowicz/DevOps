# DevOps AWS Monitoring & Database Stack

Terraform + Ansible workflow for provisioning a monitoring and database stack in AWS.

## Architecture

**Terraform** (`terraform-infra/`)
- VPC with public & private subnets
- EC2 instances in private subnets (monitoring-node, database-node)
- Application Load Balancer for Grafana access
- SSM Parameter Store for secrets
- Daily EBS snapshot lifecycle policy

**Ansible** (`playbooks/`)
- K3s & Helm installation
- Prometheus/Grafana deployment via Helm
- Node & PostgreSQL exporters
- Cross-instance metrics scraping

**Tests** (`tests/`)
- PostgreSQL connectivity validation
- API functional and non-functional tests

## Quick Start

```bash
cd terraform-infra
terraform init && terraform apply

cd ../playbooks
ansible-playbook k3s-setup.yml
ansible-playbook deploy-monitoring.yml
ansible-playbook deploy-database.yml
```

## Access

- **Grafana**: `http://<ALB_DNS_NAME>` (user: admin, password in SSM)
- **Prometheus**: `kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090`
- **PostgreSQL**: `psql -h <db_private_ip> -p 30432 -U postgres -d appdb`

## Requirements

- Terraform 1.5+
- Ansible 2.15+ with `amazon.aws` and `kubernetes.core` collections
- AWS CLI with Session Manager plugin

## Tear-down

```bash
terraform destroy
```
