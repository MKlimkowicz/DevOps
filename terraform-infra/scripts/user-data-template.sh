#!/bin/bash
set -e

# Variables from Terraform
PROJECT_NAME="${project_name}"
ENVIRONMENT="${environment}"
INSTANCE_NAME="${instance_name}"

# Enhanced logging setup with error handling
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
echo "Starting user data script for $${INSTANCE_NAME} instance at $(date)"

# Function for error handling
error_exit() {
    echo "ERROR: $1" >&2
    echo "User data script failed at $(date)" >&2
    exit 1
}

# Function for retrying commands
retry_command() {
    local retries=3
    local count=0
    until [ $count -ge $retries ]; do
        if "$@"; then
            break
        fi
        count=$((count+1))
        echo "Command failed. Attempt $count of $retries. Retrying in 10 seconds..."
        sleep 10
    done
    if [ $count -ge $retries ]; then
        error_exit "Command failed after $retries attempts: $*"
    fi
}

# Update system with retry
echo "Updating system packages..."
retry_command dnf update -y --allowerasing --skip-broken

# Install required packages with retry and validation
echo "Installing required packages..."
retry_command dnf install -y docker git wget unzip htop tree amazon-cloudwatch-agent awscli amazon-ssm-agent

# Validate critical packages are installed
command -v docker >/dev/null 2>&1 || error_exit "Docker installation failed"
command -v aws >/dev/null 2>&1 || error_exit "AWS CLI installation failed"
command -v wget >/dev/null 2>&1 || error_exit "wget installation failed"

# Ensure SSM agent is installed and running
echo "Configuring SSM agent..."
retry_command dnf install -y amazon-ssm-agent
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent
systemctl status amazon-ssm-agent --no-pager

# Verify SSM agent is connecting
echo "Waiting for SSM agent to register..."
sleep 30

# Start and enable Docker
systemctl start docker
systemctl enable docker
usermod -aG docker ec2-user

# Create directories
mkdir -p /opt/k8s/{manifests,configs,logs}
mkdir -p /data/{prometheus,grafana,postgresql}
mkdir -p /opt/terraform-scripts
chown -R ec2-user:ec2-user /opt/k8s /data

# Mount additional EBS volume
sleep 10
DEVICE=""
if [ -b /dev/nvme1n1 ]; then
    DEVICE="/dev/nvme1n1"
elif [ -b /dev/xvdf ]; then
    DEVICE="/dev/xvdf"
fi

if [ -n "$DEVICE" ] && ! mountpoint -q /data; then
    if ! blkid $DEVICE; then
        mkfs.ext4 $DEVICE
    fi
    mount $DEVICE /data
    echo "$DEVICE /data ext4 defaults,nofail 0 2" >> /etc/fstab
    chown -R ec2-user:ec2-user /data
fi

# Configure CloudWatch agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
{
    "agent": {
        "metrics_collection_interval": 60,
        "run_as_user": "cwagent"
    },
    "metrics": {
        "namespace": "${project_name}/${environment}",
        "metrics_collected": {
            "cpu": {
                "measurement": ["cpu_usage_idle", "cpu_usage_user", "cpu_usage_system"],
                "metrics_collection_interval": 60
            },
            "disk": {
                "measurement": ["used_percent"],
                "metrics_collection_interval": 60,
                "resources": ["*"]
            },
            "mem": {
                "measurement": ["mem_used_percent"],
                "metrics_collection_interval": 60
            }
        }
    },
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/var/log/user-data.log",
                        "log_group_name": "/aws/ec2/${project_name}-${environment}",
                        "log_stream_name": "{instance_id}/user-data.log"
                    }
                ]
            }
        }
    }
}
EOF

/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s

# Create setup scripts inline since we can't reference external files in user-data
%{ for script in scripts ~}
%{ if script == "install-k3s.sh" ~}
cat > /opt/terraform-scripts/install-k3s.sh << 'SCRIPT_EOF'
#!/bin/bash
set -e

PROJECT_NAME=$1
ENVIRONMENT=$2
INSTANCE_NAME=$3

echo "Installing k3s on $INSTANCE_NAME instance..."

# Download and install k3s
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--write-kubeconfig-mode 644 --disable traefik --data-dir /data/k3s" sh -

# Wait for k3s to be ready
echo "Waiting for k3s to be ready..."
sleep 30

# Verify k3s installation
kubectl get nodes

# Install Helm
echo "Installing Helm..."
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Add Helm repositories
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Create kubeconfig for ec2-user
mkdir -p /home/ec2-user/.kube
cp /etc/rancher/k3s/k3s.yaml /home/ec2-user/.kube/config
chown ec2-user:ec2-user /home/ec2-user/.kube/config

# Create alias for kubectl
echo 'alias k=kubectl' >> /home/ec2-user/.bashrc
echo 'export KUBECONFIG=/home/ec2-user/.kube/config' >> /home/ec2-user/.bashrc

echo "k3s installation completed successfully"
SCRIPT_EOF
%{ endif ~}

%{ if script == "setup-monitoring.sh" ~}
cat > /opt/terraform-scripts/setup-monitoring.sh << 'SCRIPT_EOF'
#!/bin/bash
set -e

PROJECT_NAME=$1
ENVIRONMENT=$2
INSTANCE_NAME=$3

echo "Setting up monitoring stack on $INSTANCE_NAME instance..."

# Set up kubectl configuration
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# Wait for k3s to be ready
sleep 60

# Get region with fallback
AZ=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
if [ -n "$AZ" ]; then
    REGION=$(echo "$AZ" | sed 's/[a-z]$//')
else
    REGION="eu-central-1"
fi

GRAFANA_PASSWORD=$(aws ssm get-parameter --name "/$PROJECT_NAME/$ENVIRONMENT/grafana/admin-password" --with-decryption --query 'Parameter.Value' --output text --region "$REGION")

# Create monitoring namespace
kubectl create namespace monitoring || true

# Install kube-prometheus-stack
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=10Gi \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName=local-path \
  --set prometheus.prometheusSpec.retention=7d \
  --set grafana.adminPassword="$GRAFANA_PASSWORD" \
  --set grafana.persistence.enabled=true \
  --set grafana.persistence.size=5Gi \
  --set grafana.persistence.storageClassName=local-path \
  --set grafana.service.type=NodePort \
  --set grafana.service.nodePort=30000 \
  --set prometheus.service.type=NodePort \
  --set prometheus.service.nodePort=30001 \
  --set alertmanager.service.type=NodePort \
  --set alertmanager.service.nodePort=30002 \
  --set grafana.sidecar.datasources.enabled=true \
  --set grafana.sidecar.dashboards.enabled=true \
  --set grafana.sidecar.dashboards.label=grafana_dashboard \
  --set grafana.sidecar.datasources.label=grafana_datasource \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
  --set prometheus.prometheusSpec.ruleSelectorNilUsesHelmValues=false

# Create port forwarding service for Grafana to work with ALB
cat > /opt/k8s/manifests/grafana-service.yaml << 'EOF'
apiVersion: v1
kind: Service
metadata:
  name: grafana-alb
  namespace: monitoring
spec:
  type: NodePort
  ports:
  - port: 3000
    targetPort: 3000
    nodePort: 30003
  selector:
    app.kubernetes.io/name: grafana
    app.kubernetes.io/instance: kube-prometheus-stack
EOF

kubectl apply -f /opt/k8s/manifests/grafana-service.yaml

# Wait for pods to be ready
echo "Waiting for monitoring stack to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=grafana -n monitoring --timeout=300s || true
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=prometheus -n monitoring --timeout=300s || true

# Add cross-instance monitoring if database exists
DATABASE_INSTANCE_IP=""
if aws ssm get-parameter --name "/$PROJECT_NAME/$ENVIRONMENT/database/private-ip" --region "$REGION" >/dev/null 2>&1; then
    DATABASE_INSTANCE_IP=$(aws ssm get-parameter --name "/$PROJECT_NAME/$ENVIRONMENT/database/private-ip" --query 'Parameter.Value' --output text --region "$REGION" 2>/dev/null)
    echo "Database instance detected at IP: $DATABASE_INSTANCE_IP"
    
    # Create additional scrape configuration for database instance
    cat > /opt/k8s/manifests/database-monitoring.yaml << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: additional-scrape-configs
  namespace: monitoring
data:
  additional.yaml: |
    - job_name: 'database-node-exporter'
      static_configs:
        - targets: ['DATABASE_IP:30100']
      metrics_path: /metrics
      scrape_interval: 30s
    - job_name: 'database-postgres-exporter'
      static_configs:
        - targets: ['DATABASE_IP:30187']
      metrics_path: /metrics
      scrape_interval: 30s
EOF
    
    # Replace placeholder with actual IP
    sed -i "s/DATABASE_IP/$DATABASE_INSTANCE_IP/g" /opt/k8s/manifests/database-monitoring.yaml
    kubectl apply -f /opt/k8s/manifests/database-monitoring.yaml
    kubectl patch prometheus kube-prometheus-stack-prometheus -n monitoring --type='merge' -p='{"spec":{"additionalScrapeConfigs":{"name":"additional-scrape-configs","key":"additional.yaml"}}}'
    echo "Cross-instance monitoring configured"
fi

echo "Monitoring stack setup completed successfully"
SCRIPT_EOF
%{ endif ~}

%{ if script == "setup-database.sh" ~}
cat > /opt/terraform-scripts/setup-database.sh << 'SCRIPT_EOF'
#!/bin/bash
set -e

PROJECT_NAME=$1
ENVIRONMENT=$2
INSTANCE_NAME=$3

echo "Setting up PostgreSQL database on $INSTANCE_NAME instance..."

# Set up kubectl configuration
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# Wait for k3s to be ready
sleep 60

# Get region with fallback
AZ=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
if [ -n "$AZ" ]; then
    REGION=$(echo "$AZ" | sed 's/[a-z]$//')
else
    REGION="eu-central-1"
fi

POSTGRES_PASSWORD=$(aws ssm get-parameter --name "/$PROJECT_NAME/$ENVIRONMENT/postgres/password" --with-decryption --query 'Parameter.Value' --output text --region "$REGION")

# Create database namespace
kubectl create namespace database || true

# Install PostgreSQL using Bitnami chart
helm upgrade --install postgresql bitnami/postgresql \
  --namespace database \
  --set auth.postgresPassword="$POSTGRES_PASSWORD" \
  --set auth.database="appdb" \
  --set primary.persistence.enabled=true \
  --set primary.persistence.size=10Gi \
  --set primary.persistence.storageClass=local-path \
  --set primary.service.type=NodePort \
  --set primary.service.nodePorts.postgresql=30432 \
  --set metrics.enabled=true \
  --set metrics.serviceMonitor.enabled=true \
  --set metrics.serviceMonitor.namespace=monitoring

# Install node-exporter for system metrics
helm upgrade --install node-exporter prometheus-community/prometheus-node-exporter \
  --namespace monitoring \
  --create-namespace \
  --set service.type=NodePort \
  --set service.nodePort=30100 \
  --set hostRootFsMount.enabled=true \
  --set hostRootFsMount.mountPropagation=HostToContainer

# Create service to expose PostgreSQL exporter metrics
cat > /opt/k8s/manifests/postgres-exporter-service.yaml << 'EOF'
apiVersion: v1
kind: Service
metadata:
  name: postgres-exporter-external
  namespace: database
spec:
  type: NodePort
  ports:
  - port: 9187
    targetPort: 9187
    nodePort: 30187
  selector:
    app.kubernetes.io/name: postgresql-metrics
    app.kubernetes.io/instance: postgresql
EOF

kubectl apply -f /opt/k8s/manifests/postgres-exporter-service.yaml

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgresql -n database --timeout=300s || true

echo "PostgreSQL database setup completed successfully"
SCRIPT_EOF
%{ endif ~}

chmod +x /opt/terraform-scripts/*.sh
%{ endfor ~}

# Execute setup scripts
%{ for script in scripts ~}
echo "Executing ${script}..."
bash /opt/terraform-scripts/${script} "$PROJECT_NAME" "$ENVIRONMENT" "$INSTANCE_NAME"
%{ endfor ~}

echo "User data script completed at $(date)" 