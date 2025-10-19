# DevOps Infrastructure Playbooks

This directory contains Ansible playbooks to replace shell scripts for infrastructure management.

## Phase 1: Foundation & Infrastructure Bootstrap

### Overview
Phase 1 replaces the foundational shell scripts with Ansible playbooks:
- `install-k3s.sh` → `k3s-setup.yml`
- `setup-security.sh` → `security-setup.yml`

### Prerequisites

1. **Quick Setup** (recommended):
   ```bash
   cd playbooks
   ./setup-ansible-aws.sh
   ```

2. **Manual Setup**:
   ```bash
   pip install ansible kubernetes boto3 botocore
   ansible-galaxy collection install -r requirements.yml
   # Install AWS Session Manager plugin (see setup script for details)
   ```

3. **AWS CLI configured** with appropriate permissions
4. **AWS Session Manager plugin** installed

### Playbooks

#### 1. Security Setup (`security-setup.yml`)
Replaces `setup-security.sh` - updates Terraform configuration with current public IP.

**Usage:**
```bash
cd playbooks
ansible-playbook security-setup.yml
```

**What it does:**
- ✅ Fetches your current public IP
- ✅ Updates `terraform.tfvars` with IP restrictions
- ✅ Creates backup of existing configuration
- ✅ Validates the changes

#### 2. K3s Setup (`k3s-setup.yml`)
Replaces `install-k3s.sh` - installs and configures K3s cluster with Helm.

**Usage:**
```bash
cd playbooks
ansible-playbook k3s-setup.yml
```

**What it does:**
- ✅ Connects via AWS SSM Session Manager (no SSH keys needed!)
- ✅ Installs K3s with custom configuration
- ✅ Installs Helm package manager
- ✅ Adds required Helm repositories (prometheus-community, bitnami)
- ✅ Configures kubectl access for ec2-user
- ✅ Sets up log rotation
- ✅ Verifies cluster functionality

### Configuration

#### Inventory (`inventory/hosts.yml`)
Pre-configured with your Terraform output:
```yaml
application-instance:
  ansible_host: "10.0.20.100"          # Application private IP
  instance_id: "i-0435f6706410db9e5"   # Application instance

monitoring-instance:
  ansible_host: "10.0.10.254"          # Monitoring private IP  
  instance_id: "i-02707a64f9c2b283f"   # Monitoring instance
```

**Connection Method**: AWS SSM Session Manager (no bastion/VPN needed!)
Dynamic inventory via `inventory/aws_ec2.yml` (requires tags).

#### Variables (`group_vars/all.yml`)
Global configuration for all playbooks:
- Project name and deployment environment
- K3s and Helm versions
- Directory paths
- Network settings

##### Safety toggles
- `allow_format_data_volume` (default: false): allow creating filesystem on data volume if none exists.
- `force_reinit_postgresql_data` (default: false): wipe `/data/postgresql/*` before deploy.
- `wipe_postgres_release` (default: false): uninstall Helm release and delete PVCs before deploy.

Usage examples:
```bash
# Format data volume on first bootstrap (explicit opt-in)
ansible-playbook k3s-setup.yml -e allow_format_data_volume=true

# Reinitialize Postgres data (DANGEROUS)
ansible-playbook deploy-postgresql.yml -e force_reinit_postgresql_data=true

# Fully wipe release and PVCs (DANGEROUS)
ansible-playbook deploy-postgresql.yml -e wipe_postgres_release=true
```

### Testing Phase 1

1. **Setup Dependencies**:
   ```bash
   cd playbooks
   ./setup-ansible-aws.sh
   ```

2. **Test Security Setup** (local):
   ```bash
   ansible-playbook security-setup.yml
   # Check: terraform.tfvars should have your current IP
   ```

3. **Test K3s Installation** (remote via SSM):
   ```bash
   # First, ensure infrastructure is deployed
   cd ../terraform-infra
   terraform apply
   
   # Then install K3s via Ansible
   cd ../playbooks
   ansible-playbook k3s-setup.yml
   
   # Verify via SSM Session Manager
   aws ssm start-session --target i-0435f6706410db9e5
   # In the session:
   kubectl get nodes
   helm list
   ```

### Connection Details

**AWS SSM Session Manager**: 
- ✅ No SSH keys or bastion hosts required
- ✅ Works with private instances
- ✅ All traffic encrypted and logged
- ✅ IAM-based access control

**Manual SSH Alternative** (if you have VPN/bastion):
```bash
# Connect directly (requires network access to private IPs)
ssh -i ~/.ssh/your-key ec2-user@10.0.20.100
ssh -i ~/.ssh/your-key ec2-user@10.0.10.254
```

### Advantages over Shell Scripts

| Feature | Shell Scripts | Ansible Playbooks |
|---------|---------------|-------------------|
| **Idempotency** | ❌ Manual checks | ✅ Built-in |
| **Error Handling** | ❌ Basic | ✅ Comprehensive |
| **Logging** | ❌ Limited | ✅ Structured |
| **Rollback** | ❌ Manual | ✅ Automated |
| **Variables** | ❌ Hardcoded | ✅ Templated |
| **Validation** | ❌ None | ✅ Built-in |
| **Connection** | ❌ SSH keys/bastion | ✅ AWS SSM |

### Next Phases
- **Phase 2**: Node Exporter + System Bootstrap
- **Phase 3**: PostgreSQL Chart
- **Phase 4**: Monitoring Stack Chart
- **Phase 5**: Advanced Bootstrap Templates

### Troubleshooting

**Common Issues:**

1. **SSM Connection Failed**:
   ```bash
   # Test SSM connectivity
   aws ssm start-session --target i-0435f6706410db9e5
   
   # Check IAM permissions for SSM
   aws sts get-caller-identity
   ```

2. **Ansible Collection Missing**:
   ```bash
   ansible-galaxy collection install amazon.aws --force
   ```

3. **Session Manager Plugin Missing**:
   ```bash
   # Run setup script or install manually
   ./setup-ansible-aws.sh
   ```

4. **AWS Credentials**:
   ```bash
   aws configure
   # or set environment variables:
   export AWS_ACCESS_KEY_ID=your_key
   export AWS_SECRET_ACCESS_KEY=your_secret
   ``` 