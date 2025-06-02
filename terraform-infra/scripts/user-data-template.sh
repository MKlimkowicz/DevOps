#!/bin/bash
set -e

# Variables from Terraform
PROJECT_NAME="${project_name}"
ENVIRONMENT="${environment}"
INSTANCE_NAME="${instance_name}"
DEPLOY_DATABASE="${deploy_database}"

# Enhanced logging setup with error handling
exec > >(tee /var/log/user-data.log) 2>&1
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
{"agent":{"metrics_collection_interval":60,"run_as_user":"cwagent"},"metrics":{"namespace":"${project_name}/${environment}","metrics_collected":{"cpu":{"measurement":["cpu_usage_idle","cpu_usage_user","cpu_usage_system"],"metrics_collection_interval":60},"disk":{"measurement":["used_percent"],"metrics_collection_interval":60,"resources":["*"]},"mem":{"measurement":["mem_used_percent"],"metrics_collection_interval":60}}},"logs":{"logs_collected":{"files":{"collect_list":[{"file_path":"/var/log/user-data.log","log_group_name":"/aws/ec2/${project_name}-${environment}","log_stream_name":"{instance_id}/user-data.log"}]}}}}
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
DEPLOY_DATABASE=$4

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
for i in {1..60}; do
    if aws ssm get-parameter --name "/$PROJECT_NAME/$ENVIRONMENT/database/private-ip" --region "$REGION" >/dev/null 2>&1; then
        DATABASE_INSTANCE_IP=$(aws ssm get-parameter --name "/$PROJECT_NAME/$ENVIRONMENT/database/private-ip" --query 'Parameter.Value' --output text --region "$REGION" 2>/dev/null)
        if [ -n "$DATABASE_INSTANCE_IP" ] && [ "$DATABASE_INSTANCE_IP" != "None" ]; then
            echo "Database instance detected at IP: $DATABASE_INSTANCE_IP"
            break
        fi
    fi
    echo "Attempt $i/60: Waiting for database instance IP to be available..."
    sleep 10
done

if [ -n "$DATABASE_INSTANCE_IP" ] && [ "$DATABASE_INSTANCE_IP" != "None" ]; then
    echo "Setting up monitoring for database instance at $DATABASE_INSTANCE_IP..."
    
    # Test connectivity to database exporters
    echo "Testing connectivity to database instance..."
    
    # Test Node Exporter
    NODE_EXPORTER_OK=false
    for i in {1..5}; do
        if timeout 10 curl -f -s "http://$${DATABASE_INSTANCE_IP}:30100/metrics" > /dev/null 2>&1; then
            echo "✅ Node Exporter accessible on $${DATABASE_INSTANCE_IP}:30100"
            NODE_EXPORTER_OK=true
            break
        else
            echo "Attempt $i/5: Testing Node Exporter connectivity..."
            if [ $i -eq 5 ]; then
                echo "❌ Cannot reach Node Exporter on $${DATABASE_INSTANCE_IP}:30100"
            fi
            sleep 5
        fi
    done
    
    # Test PostgreSQL Exporter
    POSTGRES_EXPORTER_OK=false
    for i in {1..5}; do
        if timeout 10 curl -f -s "http://$${DATABASE_INSTANCE_IP}:30187/metrics" > /dev/null 2>&1; then
            PG_UP_VALUE=$(timeout 10 curl -s "http://$${DATABASE_INSTANCE_IP}:30187/metrics" 2>/dev/null | grep "pg_up" | head -1 | awk '{print $2}' || echo "0")
            if [ "$PG_UP_VALUE" = "1" ]; then
                echo "✅ PostgreSQL Exporter accessible on $${DATABASE_INSTANCE_IP}:30187 and connected to PostgreSQL"
                POSTGRES_EXPORTER_OK=true
                break
            else
                echo "⚠️  PostgreSQL Exporter accessible but not connected to PostgreSQL (pg_up=$PG_UP_VALUE)"
            fi
        else
            echo "Attempt $i/5: Testing PostgreSQL Exporter connectivity..."
            if [ $i -eq 5 ]; then
                echo "❌ Cannot reach PostgreSQL Exporter on $${DATABASE_INSTANCE_IP}:30187"
            fi
            sleep 5
        fi
    done
    
    # Only proceed with scrape configuration if at least one exporter is working
    if [ "$NODE_EXPORTER_OK" = "true" ] || [ "$POSTGRES_EXPORTER_OK" = "true" ]; then
        # Create additional scrape configuration for database instance
        cat > /opt/k8s/manifests/database-monitoring.yaml << 'EOF'
apiVersion: v1
kind: Secret
metadata:
  name: additional-scrape-configs
  namespace: monitoring
stringData:
  prometheus-additional.yaml: |
    - job_name: 'database-node-exporter'
      static_configs:
        - targets: ['DATABASE_IP:30100']
          labels:
            instance_type: 'database'
            environment: 'ENVIRONMENT'
      scrape_interval: 30s
      metrics_path: /metrics
      
    - job_name: 'database-postgres-exporter'
      static_configs:
        - targets: ['DATABASE_IP:30187']
          labels:
            instance_type: 'database'
            environment: 'ENVIRONMENT'
      scrape_interval: 30s
      metrics_path: /metrics
EOF
        
        # Replace placeholders with actual values
        sed -i "s/DATABASE_IP/$${DATABASE_INSTANCE_IP}/g" /opt/k8s/manifests/database-monitoring.yaml
        sed -i "s/ENVIRONMENT/$${ENVIRONMENT}/g" /opt/k8s/manifests/database-monitoring.yaml
        kubectl apply -f /opt/k8s/manifests/database-monitoring.yaml
        kubectl patch prometheus kube-prometheus-stack-prometheus -n monitoring --type='merge' -p='{"spec":{"additionalScrapeConfigs":{"name":"additional-scrape-configs","key":"prometheus-additional.yaml"}}}'
        echo "✅ Cross-instance monitoring configured"
    else
        echo "❌ No database exporters accessible - skipping monitoring configuration"
    fi
else
    echo "⚠️  Database instance IP not found or invalid - skipping cross-instance monitoring"
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

# Wait for k3s to be ready and verify it's working
echo "Waiting for k3s to be ready..."
sleep 60

# Wait for k3s to be fully ready
until kubectl cluster-info >/dev/null 2>&1; do
    echo "Waiting for k3s cluster to be ready..."
    sleep 10
done
echo "k3s cluster is ready"

# Get PostgreSQL password from Parameter Store
echo "Getting region from metadata..."
AZ=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone 2>/dev/null)
if [ -n "$AZ" ]; then
    REGION=$(echo "$AZ" | sed 's/[a-z]$//')
else
    # Fallback to eu-central-1 if metadata fails
    REGION="eu-central-1"
fi
echo "Using AWS region: $REGION"

echo "Retrieving PostgreSQL password from Parameter Store..."
POSTGRES_PASSWORD=$(aws ssm get-parameter --name "/$PROJECT_NAME/$ENVIRONMENT/postgres/password" --with-decryption --query 'Parameter.Value' --output text --region "$REGION")

if [ -z "$POSTGRES_PASSWORD" ]; then
    echo "ERROR: Failed to retrieve PostgreSQL password from Parameter Store"
    exit 1
fi

# Create database namespace
echo "Creating database namespace..."
kubectl create namespace database || true

# Create secret for PostgreSQL password
echo "Creating PostgreSQL secret..."
kubectl delete secret postgres-secret -n database 2>/dev/null || true
kubectl create secret generic postgres-secret \
  --from-literal=postgres-password="$POSTGRES_PASSWORD" \
  --namespace database

# Install PostgreSQL using Bitnami chart with comprehensive configuration
echo "Installing PostgreSQL via Helm..."
helm upgrade --install postgresql bitnami/postgresql \
  --namespace database \
  --set auth.postgresPassword="$POSTGRES_PASSWORD" \
  --set auth.database="appdb" \
  --set auth.enablePostgresUser=true \
  --set primary.persistence.enabled=true \
  --set primary.persistence.size=10Gi \
  --set primary.persistence.storageClass=local-path \
  --set primary.service.type=NodePort \
  --set primary.service.nodePorts.postgresql=30432 \
  --set metrics.enabled=false \
  --set metrics.serviceMonitor.enabled=false \
  --set metrics.prometheusRule.enabled=false \
  --wait \
  --timeout=10m

# Wait for PostgreSQL to be ready with better error handling
echo "Waiting for PostgreSQL pods to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgresql -n database --timeout=600s

# Verify PostgreSQL is responding
echo "Verifying PostgreSQL is responding..."
sleep 30

# Get the PostgreSQL pod name with error handling
POSTGRES_POD=$(kubectl get pods -n database -l app.kubernetes.io/name=postgresql -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POSTGRES_POD" ]; then
    echo "ERROR: No PostgreSQL pod found"
    kubectl get pods -n database
    exit 1
fi

echo "PostgreSQL pod: $POSTGRES_POD"

# Test database connectivity before creating schema
echo "Testing database connectivity..."
kubectl exec -n database "$POSTGRES_POD" -- psql -U postgres -d appdb -c "SELECT version();"

# Create sample database and table with better error handling
echo "Creating sample database schema and data..."
kubectl exec -n database "$POSTGRES_POD" -- psql -U postgres -d appdb -c "
-- Create schema
CREATE TABLE IF NOT EXISTS sample_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    instance_id VARCHAR(50) NOT NULL
);

-- Clear existing data and insert fresh samples
DELETE FROM sample_metrics;

INSERT INTO sample_metrics (metric_name, metric_value, instance_id) VALUES
('cpu_usage', 45.2, 'i-1234567890abcdef0'),
('memory_usage', 67.8, 'i-1234567890abcdef0'),
('disk_usage', 23.1, 'i-1234567890abcdef0'),
('network_in', 125.4, 'i-1234567890abcdef0'),
('network_out', 89.2, 'i-1234567890abcdef0');

-- Verify data
SELECT COUNT(*) as sample_count FROM sample_metrics;
"

# Create directory for manifests
mkdir -p /opt/k8s/manifests

# Install Node Exporter for system metrics monitoring
echo "Installing Node Exporter..."
cat > /opt/k8s/manifests/node-exporter.yaml << 'EOF'
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: database
  labels:
    app: node-exporter
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
      hostPID: true
      containers:
      - name: node-exporter
        image: prom/node-exporter:v1.7.0
        args:
          - '--path.procfs=/host/proc'
          - '--path.sysfs=/host/sys'
          - '--path.rootfs=/host/root'
          - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
        ports:
        - containerPort: 9100
          hostPort: 9100
          name: metrics
        volumeMounts:
        - name: proc
          mountPath: /host/proc
          readOnly: true
        - name: sys
          mountPath: /host/sys
          readOnly: true
        - name: root
          mountPath: /host/root
          readOnly: true
        resources:
          limits:
            cpu: 100m
            memory: 128Mi
          requests:
            cpu: 50m
            memory: 64Mi
      volumes:
      - name: proc
        hostPath:
          path: /proc
      - name: sys
        hostPath:
          path: /sys
      - name: root
        hostPath:
          path: /
---
apiVersion: v1
kind: Service
metadata:
  name: node-exporter
  namespace: database
  labels:
    app: node-exporter
spec:
  ports:
  - port: 9100
    targetPort: 9100
    nodePort: 30100
    name: metrics
  selector:
    app: node-exporter
  type: NodePort
EOF

# Apply Node Exporter manifest with retry logic
echo "Applying Node Exporter manifest..."
for i in {1..3}; do
    if kubectl apply -f /opt/k8s/manifests/node-exporter.yaml; then
        echo "✅ Node Exporter manifest applied successfully"
        break
    else
        echo "Attempt $i/3: Failed to apply Node Exporter manifest, retrying in 10 seconds..."
        sleep 10
        if [ $i -eq 3 ]; then
            echo "❌ Failed to apply Node Exporter manifest after 3 attempts"
            exit 1
        fi
    fi
done

# Wait for node-exporter to be ready with better error handling
echo "Waiting for Node Exporter to be ready..."
if ! kubectl wait --for=condition=ready pod -l app=node-exporter -n database --timeout=300s; then
    echo "❌ Node Exporter failed to become ready. Checking status..."
    kubectl get pods -n database -l app=node-exporter
    kubectl describe daemonset node-exporter -n database
    exit 1
fi
echo "✅ Node Exporter is ready"

# Verify Node Exporter is working
echo "Verifying Node Exporter functionality..."
for i in {1..10}; do
    if curl -f -s http://localhost:30100/metrics > /dev/null; then
        echo "✅ Node Exporter is responding on port 30100"
        break
    else
        echo "Attempt $i/10: Node Exporter not responding, waiting 5 seconds..."
        if [ $i -eq 10 ]; then
            echo "❌ Node Exporter not responding after 10 attempts"
            kubectl logs -n database daemonset/node-exporter --tail=20
        fi
        sleep 5
    fi
done

# Install PostgreSQL Exporter for Prometheus monitoring
echo "Installing PostgreSQL Exporter..."

# Get the PostgreSQL password and URL-encode it to handle special characters
echo "Getting PostgreSQL password and URL-encoding it..."
for i in {1..5}; do
    POSTGRES_PASSWORD_RAW=$(kubectl get secret postgresql -n database -o jsonpath='{.data.postgres-password}' 2>/dev/null | base64 -d 2>/dev/null)
    if [ -n "$POSTGRES_PASSWORD_RAW" ]; then
        echo "✅ Retrieved PostgreSQL password"
        break
    else
        echo "Attempt $i/5: Waiting for PostgreSQL secret to be available..."
        sleep 5
        if [ $i -eq 5 ]; then
            echo "❌ Could not retrieve PostgreSQL password"
            kubectl get secrets -n database
            exit 1
        fi
    fi
done

# URL-encode special characters that could break the connection string
POSTGRES_PASSWORD_ENCODED=$(echo "$POSTGRES_PASSWORD_RAW" | sed 's/#/%23/g; s/(/%28/g; s/)/%29/g; s/\[/%5B/g; s/\]/%5D/g; s/@/%40/g; s/\//%2F/g; s/?/%3F/g; s/&/%26/g; s/=/%3D/g; s/ /%20/g')

cat > /opt/k8s/manifests/postgres-exporter.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres-exporter
  namespace: database
  labels:
    app: postgres-exporter
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
        ports:
        - containerPort: 9187
          name: metrics
        env:
        - name: DATA_SOURCE_NAME
          value: "postgresql://postgres:$POSTGRES_PASSWORD_ENCODED@postgresql.database.svc.cluster.local:5432/appdb?sslmode=disable"
        resources:
          limits:
            cpu: 100m
            memory: 128Mi
          requests:
            cpu: 50m
            memory: 64Mi
        livenessProbe:
          httpGet:
            path: /metrics
            port: 9187
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /metrics
            port: 9187
          initialDelaySeconds: 10
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-exporter
  namespace: database
  labels:
    app: postgres-exporter
spec:
  ports:
  - port: 9187
    targetPort: 9187
    nodePort: 30187
    name: metrics
  selector:
    app: postgres-exporter
  type: NodePort
EOF

# Apply PostgreSQL Exporter manifest with retry logic
echo "Applying PostgreSQL Exporter manifest..."
for i in {1..3}; do
    if kubectl apply -f /opt/k8s/manifests/postgres-exporter.yaml; then
        echo "✅ PostgreSQL Exporter manifest applied successfully"
        break
    else
        echo "Attempt $i/3: Failed to apply PostgreSQL Exporter manifest, retrying in 10 seconds..."
        sleep 10
        if [ $i -eq 3 ]; then
            echo "❌ Failed to apply PostgreSQL Exporter manifest after 3 attempts"
            exit 1
        fi
    fi
done

# Wait for postgres-exporter to be ready with better error handling
echo "Waiting for PostgreSQL Exporter to be ready..."
if ! kubectl wait --for=condition=ready pod -l app=postgres-exporter -n database --timeout=300s; then
    echo "❌ PostgreSQL Exporter failed to become ready. Checking status..."
    kubectl get pods -n database -l app=postgres-exporter
    kubectl describe deployment postgres-exporter -n database
    kubectl logs -n database deployment/postgres-exporter --tail=20
    exit 1
fi
echo "✅ PostgreSQL Exporter is ready"

# Comprehensive verification of PostgreSQL Exporter
echo "Verifying PostgreSQL Exporter functionality..."
sleep 15  # Give exporter time to initialize

# Test if the exporter is accessible locally and can connect to PostgreSQL
EXPORTER_WORKING=false
for i in {1..15}; do
    echo "Attempt $i/15: Testing PostgreSQL Exporter connectivity..."
    
    # Test basic connectivity
    if ! curl -f -s http://localhost:30187/metrics > /dev/null; then
        echo "   PostgreSQL Exporter not responding on port 30187, waiting 10 seconds..."
        sleep 10
        continue
    fi
    
    # Test PostgreSQL connection via pg_up metric
    EXPORTER_RESPONSE=$(curl -s http://localhost:30187/metrics 2>/dev/null || echo "")
    if echo "$EXPORTER_RESPONSE" | grep -q "pg_up"; then
        PG_UP_VALUE=$(echo "$EXPORTER_RESPONSE" | grep "pg_up" | head -1 | awk '{print $2}')
        if [ "$PG_UP_VALUE" = "1" ]; then
            echo "✅ PostgreSQL Exporter is responding correctly and connected to PostgreSQL"
            EXPORTER_WORKING=true
            break
        else
            echo "   PostgreSQL Exporter responding but not connected to PostgreSQL (pg_up=$PG_UP_VALUE)"
            echo "   Checking PostgreSQL connectivity..."
            
            # Test direct PostgreSQL connection
            if kubectl exec -n database postgresql-0 -- psql -U postgres -d appdb -c "SELECT 1;" > /dev/null 2>&1; then
                echo "   PostgreSQL is accessible, checking exporter logs..."
                kubectl logs -n database deployment/postgres-exporter --tail=10
            else
                echo "   PostgreSQL is not accessible, this is the root cause"
            fi
        fi
    else
        echo "   PostgreSQL Exporter responding but no pg_up metric found"
    fi
    
    sleep 10
done

if [ "$EXPORTER_WORKING" = "false" ]; then
    echo "❌ PostgreSQL Exporter failed to connect to PostgreSQL after 15 attempts"
    echo "   Continuing setup, but PostgreSQL monitoring will not work properly"
fi

# Get instance private IP
PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/private-ipv4 2>/dev/null || echo "unknown")

# Store private IP in Parameter Store for cross-instance monitoring
echo "Storing database instance IP in Parameter Store..."
aws ssm put-parameter \
    --name "/$PROJECT_NAME/$ENVIRONMENT/database/private-ip" \
    --value "$PRIVATE_IP" \
    --type "String" \
    --overwrite \
    --region "$REGION" || echo "Warning: Could not store IP in Parameter Store"

echo "============================================"
echo "✅ PostgreSQL database setup completed successfully!"
echo "============================================"
echo "📍 Database Access Information:"
echo "   Host: $PRIVATE_IP"
echo "   Port: 30432"
echo "   Database: appdb"
echo "   Username: postgres"
echo "   Password: Stored in Parameter Store at /$PROJECT_NAME/$ENVIRONMENT/postgres/password"
echo ""
echo "🔧 Kubernetes Services:"
kubectl get svc -n database
echo ""
echo "📊 Database Status:"
kubectl get pods -n database
echo "============================================"

SCRIPT_EOF
%{ endif ~}

chmod +x /opt/terraform-scripts/*.sh
%{ endfor ~}

# Execute setup scripts
%{ for script in scripts ~}
echo "Executing ${script}..."
%{ if script == "setup-monitoring.sh" ~}
bash /opt/terraform-scripts/${script} "$PROJECT_NAME" "$ENVIRONMENT" "$INSTANCE_NAME" "$DEPLOY_DATABASE"
%{ else ~}
bash /opt/terraform-scripts/${script} "$PROJECT_NAME" "$ENVIRONMENT" "$INSTANCE_NAME"
%{ endif ~}
%{ endfor ~}

echo "User data script completed at $(date)" 