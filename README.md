# DevOps AWS Monitoring & Database Stack

This repository contains an opinionated **Terraform + Ansible** workflow that provisions and configures a small, self-contained monitoring and database laboratory in AWS.

## 🗺️  What gets deployed?

1. **Terraform** (`terraform-infra/`)
   - VPC with public & private subnets
   - Two Amazon Linux EC2 instances placed in private subnets
     - **monitoring-node** – runs K3s, Prometheus & Grafana
     - **database-node** (optional) – runs PostgreSQL + exporters
   - Security groups that only expose:
     - port 80 via an Application Load Balancer → Grafana ( `/login` )
     - Node / PostgreSQL exporter ports inside the VPC
     - SSH access via **AWS SSM Session Manager** (no keys exposed)
   - SSM Parameter Store secrets (Grafana admin pass, PostgreSQL pass, private SSH key)
   - Daily EBS snapshot lifecycle policy

2. **Ansible** (`playbooks/`)
   - Post-provision configuration executed over SSM:
     - Install K3s & Helm
     - Deploy Prometheus / Grafana Helm charts
     - Install Node & Postgres exporters on the database node
     - Create a Prometheus *additionalScrapeConfigs* secret to **cross-scrape** metrics from the database node
   - Auxiliary playbooks for security hardening, debugging and password retrieval

3. **Tests** (`tests/`)
   - Pytest helpers that validate PostgreSQL connectivity using credentials retrieved from SSM.

<p align="center">
  <img src="https://raw.githubusercontent.com/your-repo/docs/architecture.svg" width="600" alt="Architecture diagram">
</p>

## 🚀 Quick start

```bash
# 1. Provision infrastructure
cd terraform-infra
terraform init && terraform apply -auto-approve

# 2. Configure instances
cd ../playbooks
./setup-ansible-aws.sh       # installs collections & SSM plugin
ansible-playbook deploy-monitoring.yml     # installs K3s + monitoring stack
ansible-playbook deploy-database.yml       # (optional) installs PostgreSQL
```

Once complete Terraform outputs will show:
* **Grafana URL** – `http://<ALB_DNS_NAME>`  (user: *admin*, pass in SSM)
* **Prometheus** – port-forward from monitoring node `kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090`
* **PostgreSQL** – `psql -h <db_private_ip> -p 30432 -U postgres -d appdb`

## 🛡️  Security highlights

* Private subnets + SSM → no public SSH anywhere
* Secrets never touch git – they live in **AWS SSM Parameter Store**
* Least-privilege IAM roles for EC2, ALB & DLM snapshot service
* Ingress restricted to your current IP (updated via `playbooks/security-setup.yml`)

## 📂  Repository layout

```
DevOps/
├── terraform-infra/   # IaC modules & root module
├── playbooks/         # Ansible playbooks & inventories
├── tests/             # pytest based validation suite
└── README.md          # this file
```

## ☑️  Requirements

* Terraform 1.5+
* Ansible >=2.15 with `amazon.aws` & `kubernetes.core` collections
* AWS CLI + Session Manager plugin configured with a profile that can create the above resources

## 🧹  Tear-down

```bash
# Destroy AWS resources
tf destroy -auto-approve
# No local state is stored on instances – safe to delete.
```

