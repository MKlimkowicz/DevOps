#!/bin/bash
set -e

# Variables from Terraform
PROJECT_NAME="${project_name}"
ENVIRONMENT="${environment}"
INSTANCE_NAME="${instance_name}"
DEPLOY_DATABASE="${deploy_database}"
SCRIPTS="${scripts}"

# Setup logging
exec > >(tee /var/log/user-data.log) 2>&1
echo "Starting bootstrap for $${INSTANCE_NAME} at $(date)"

# Error handling
error_exit() { echo "ERROR: $1" >&2; exit 1; }

# Basic system setup
dnf update -y --allowerasing --skip-broken || error_exit "System update failed"
dnf install -y docker git wget unzip awscli amazon-ssm-agent || error_exit "Package installation failed"

# Validate installations
command -v docker >/dev/null 2>&1 || error_exit "Docker not found"
command -v aws >/dev/null 2>&1 || error_exit "AWS CLI not found"

# Start services
systemctl enable --now docker amazon-ssm-agent
usermod -aG docker ec2-user

# Create directories
mkdir -p /opt/{k8s/{manifests,configs,logs},terraform-scripts} /data/{prometheus,grafana,postgresql}
chown -R ec2-user:ec2-user /opt/k8s /data

# Mount EBS volume
sleep 10
for dev in nvme1n1 xvdf; do
    if [ -b "/dev/$dev" ] && ! mountpoint -q /data; then
        mkfs.ext4 -F "/dev/$dev" 2>/dev/null || true
        mount "/dev/$dev" /data
        echo "/dev/$dev /data ext4 defaults,nofail 0 2" >> /etc/fstab
        chown -R ec2-user:ec2-user /data
        break
    fi
done

# Setup CloudWatch agent
if command -v amazon-cloudwatch-agent-ctl >/dev/null 2>&1; then
    cat > /tmp/cw-config.json << 'EOF'
{"agent":{"run_as_user":"cwagent"},"metrics":{"namespace":"${project_name}/${environment}","metrics_collected":{"cpu":{"measurement":["cpu_usage_idle"],"metrics_collection_interval":300},"disk":{"measurement":["used_percent"],"metrics_collection_interval":300,"resources":["*"]},"mem":{"measurement":["mem_used_percent"],"metrics_collection_interval":300}}},"logs":{"logs_collected":{"files":{"collect_list":[{"file_path":"/var/log/user-data.log","log_group_name":"/aws/ec2/${project_name}-${environment}","log_stream_name":"{instance_id}/user-data.log"}]}}}}
EOF
    amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/tmp/cw-config.json -s
fi

# Create scripts based on what's needed
cd /opt/terraform-scripts

# K3s installer script
if echo "$SCRIPTS" | grep -q "install-k3s.sh"; then
cat > install-k3s.sh << 'EOF'
#!/bin/bash
set -e
echo "Installing k3s..."
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--write-kubeconfig-mode 644 --disable traefik --data-dir /data/k3s" sh -
sleep 30
kubectl get nodes
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
mkdir -p /home/ec2-user/.kube
cp /etc/rancher/k3s/k3s.yaml /home/ec2-user/.kube/config
chown ec2-user:ec2-user /home/ec2-user/.kube/config
echo 'alias k=kubectl' >> /home/ec2-user/.bashrc
echo "k3s installation completed"
EOF
fi

# Minimal database setup script
if echo "$SCRIPTS" | grep -q "setup-database.sh"; then
cat > setup-database.sh << 'EOF'
#!/bin/bash
set -e
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
sleep 60
until kubectl cluster-info >/dev/null 2>&1; do sleep 10; done

AZ=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
REGION=$(echo "$AZ" | sed 's/[a-z]$//' || echo "eu-central-1")
POSTGRES_PASSWORD=$(aws ssm get-parameter --name "/$1/$2/postgres/password" --with-decryption --query 'Parameter.Value' --output text --region "$REGION")

kubectl create namespace database || true
helm upgrade --install postgresql bitnami/postgresql \
  --namespace database \
  --set auth.postgresPassword="$POSTGRES_PASSWORD" \
  --set auth.database="appdb" \
  --set primary.persistence.enabled=true \
  --set primary.persistence.size=10Gi \
  --set primary.service.type=NodePort \
  --set primary.service.nodePorts.postgresql=30432 \
  --wait --timeout=10m

kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgresql -n database --timeout=600s

# Create sample data
POSTGRES_POD=$(kubectl get pods -n database -l app.kubernetes.io/name=postgresql -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n database "$POSTGRES_POD" -- psql -U postgres -d appdb -c "
CREATE TABLE IF NOT EXISTS sample_metrics (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, metric_name VARCHAR(100), metric_value FLOAT, instance_id VARCHAR(50));
INSERT INTO sample_metrics (metric_name, metric_value, instance_id) VALUES ('cpu_usage', 45.2, 'i-1234567890abcdef0'), ('memory_usage', 67.8, 'i-1234567890abcdef0'), ('disk_usage', 23.1, 'i-1234567890abcdef0');" || true

# Deploy Node Exporter
kubectl apply -f https://raw.githubusercontent.com/prometheus/node_exporter/master/examples/kubernetes/daemonset.yaml || {
    # Fallback: create minimal node exporter
    cat > /tmp/node-exporter.yaml << 'NODEEOF'
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: database
spec:
  selector:
    matchLabels:
      app: node-exporter
  template:
    metadata:
      labels:
        app: node-exporter
    spec:
      hostNetwork: true
      containers:
      - name: node-exporter
        image: prom/node-exporter:v1.7.0
        args: ['--path.procfs=/host/proc', '--path.sysfs=/host/sys', '--web.listen-address=0.0.0.0:9100']
        ports: [{ containerPort: 9100, hostPort: 9100 }]
        volumeMounts: [{ name: proc, mountPath: /host/proc, readOnly: true }, { name: sys, mountPath: /host/sys, readOnly: true }]
        securityContext: { runAsNonRoot: true, runAsUser: 65534 }
      volumes: [{ name: proc, hostPath: { path: /proc } }, { name: sys, hostPath: { path: /sys } }]
---
apiVersion: v1
kind: Service
metadata:
  name: node-exporter
  namespace: database
spec:
  ports: [{ port: 9100, nodePort: 30100, targetPort: 9100 }]
  selector: { app: node-exporter }
  type: NodePort
NODEEOF
    kubectl apply -f /tmp/node-exporter.yaml
}

# Deploy PostgreSQL Exporter
POSTGRES_PASSWORD_ENCODED=$(echo "$POSTGRES_PASSWORD" | sed 's/#/%23/g; s/@/%40/g; s/ /%20/g; s/\$/%24/g')
cat > /tmp/postgres-exporter.yaml << PGEOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres-exporter
  namespace: database
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres-exporter
  template:
    metadata:
      labels:
        app: postgres-exporter
    spec:
      containers:
      - name: postgres-exporter
        image: prometheuscommunity/postgres-exporter:v0.15.0
        ports: [{ containerPort: 9187 }]
        env: [{ name: DATA_SOURCE_NAME, value: "postgresql://postgres:$POSTGRES_PASSWORD_ENCODED@postgresql.database.svc.cluster.local:5432/appdb?sslmode=disable" }]
        livenessProbe: { httpGet: { path: /metrics, port: 9187 }, initialDelaySeconds: 60, periodSeconds: 30 }
        readinessProbe: { httpGet: { path: /metrics, port: 9187 }, initialDelaySeconds: 30, periodSeconds: 10 }
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-exporter
  namespace: database
spec:
  ports: [{ port: 9187, nodePort: 30187, targetPort: 9187 }]
  selector: { app: postgres-exporter }
  type: NodePort
PGEOF
kubectl apply -f /tmp/postgres-exporter.yaml

# Wait and verify
kubectl wait --for=condition=ready pod -l app=node-exporter -n database --timeout=300s || echo "Node exporter timeout"
kubectl wait --for=condition=ready pod -l app=postgres-exporter -n database --timeout=300s || echo "Postgres exporter timeout"

# Quick verification
sleep 30
for i in {1..5}; do
    curl -f -s http://localhost:30100/metrics >/dev/null && echo "✅ Node Exporter OK" && break
    [ $i -eq 5 ] && echo "❌ Node Exporter failed"
    sleep 10
done

for i in {1..5}; do
    if RESPONSE=$(curl -s http://localhost:30187/metrics 2>/dev/null) && echo "$RESPONSE" | grep -q "^pg_up.*1$"; then
        echo "✅ PostgreSQL Exporter OK"
        break
    fi
    [ $i -eq 5 ] && echo "❌ PostgreSQL Exporter failed"
    sleep 10
done

PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/private-ipv4)
aws ssm put-parameter --name "/$1/$2/database/private-ip" --value "$PRIVATE_IP" --type "String" --overwrite --region "$REGION" || echo "Warning: Could not store IP"
echo "✅ Database setup completed! Exporters: http://$PRIVATE_IP:30100/metrics and http://$PRIVATE_IP:30187/metrics"
EOF
fi

# Minimal monitoring setup script
if echo "$SCRIPTS" | grep -q "setup-monitoring.sh"; then
cat > setup-monitoring.sh << 'EOF'
#!/bin/bash
set -e
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
sleep 60

AZ=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
REGION=$(echo "$AZ" | sed 's/[a-z]$//' || echo "eu-central-1")
GRAFANA_PASSWORD=$(aws ssm get-parameter --name "/$1/$2/grafana/admin-password" --with-decryption --query 'Parameter.Value' --output text --region "$REGION")

kubectl create namespace monitoring || true
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=10Gi \
  --set prometheus.prometheusSpec.retention=7d \
  --set grafana.adminPassword="$GRAFANA_PASSWORD" \
  --set grafana.persistence.enabled=true \
  --set grafana.persistence.size=5Gi \
  --set grafana.service.type=NodePort \
  --set grafana.service.nodePort=30000 \
  --set prometheus.service.type=NodePort \
  --set prometheus.service.nodePort=30001 \
  --set alertmanager.service.type=NodePort \
  --set alertmanager.service.nodePort=30002 \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
  --set prometheus.prometheusSpec.ruleSelectorNilUsesHelmValues=false

# Create ALB service for Grafana
cat > /tmp/grafana-alb.yaml << 'EOF'
apiVersion: v1
kind: Service
metadata:
  name: grafana-alb
  namespace: monitoring
spec:
  type: NodePort
  ports: [{ port: 3000, targetPort: 3000, nodePort: 30003 }]
  selector: { app.kubernetes.io/name: grafana, app.kubernetes.io/instance: kube-prometheus-stack }
EOF
kubectl apply -f /tmp/grafana-alb.yaml

kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=grafana -n monitoring --timeout=300s || echo "Grafana timeout"
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=prometheus -n monitoring --timeout=300s || echo "Prometheus timeout"

# Setup database monitoring if database exists
for i in {1..30}; do
    if DATABASE_IP=$(aws ssm get-parameter --name "/$1/$2/database/private-ip" --query 'Parameter.Value' --output text --region "$REGION" 2>/dev/null) && [ -n "$DATABASE_IP" ] && [ "$DATABASE_IP" != "None" ]; then
        echo "Configuring monitoring for database at $DATABASE_IP"
        cat > /tmp/additional-scrape.yaml << EOF
apiVersion: v1
kind: Secret
metadata:
  name: additional-scrape-configs
  namespace: monitoring
stringData:
  prometheus-additional.yaml: |
    - job_name: 'database-node-exporter'
      static_configs:
        - targets: ['$DATABASE_IP:30100']
          labels: { instance_type: 'database', environment: '$2' }
      scrape_interval: 30s
    - job_name: 'database-postgres-exporter'
      static_configs:
        - targets: ['$DATABASE_IP:30187']
          labels: { instance_type: 'database', environment: '$2' }
      scrape_interval: 30s
EOF
        kubectl apply -f /tmp/additional-scrape.yaml
        kubectl patch prometheus kube-prometheus-stack-prometheus -n monitoring --type='merge' -p='{"spec":{"additionalScrapeConfigs":{"name":"additional-scrape-configs","key":"prometheus-additional.yaml"}}}'
        break
    fi
    echo "Attempt $i/30: Waiting for database IP..."
    sleep 10
done

echo "✅ Monitoring setup completed!"
EOF
fi

chmod +x *.sh

# Execute scripts
IFS=',' read -ra SCRIPT_ARRAY <<< "$SCRIPTS"
for script in "$${SCRIPT_ARRAY[@]}"; do
    if [ -f "$script" ]; then
        echo "Executing $script..."
        if [ "$script" = "setup-monitoring.sh" ]; then
            bash "$script" "$PROJECT_NAME" "$ENVIRONMENT" "$INSTANCE_NAME" "$DEPLOY_DATABASE"
        else
            bash "$script" "$PROJECT_NAME" "$ENVIRONMENT" "$INSTANCE_NAME"
        fi
    fi
done

echo "Bootstrap completed at $(date)" 