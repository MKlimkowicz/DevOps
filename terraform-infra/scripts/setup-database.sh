#!/bin/bash
set -e

PROJECT_NAME=$1
ENVIRONMENT=$2
INSTANCE_NAME=$3

echo "Setting up PostgreSQL database on $INSTANCE_NAME instance..."

# Wait for k3s to be ready and verify it's working
echo "Waiting for k3s to be ready..."
sleep 60

# Wait for k3s to be fully ready
until kubectl cluster-info >/dev/null 2>&1; do
    echo "Waiting for k3s cluster to be ready..."
    sleep 10
done
echo "k3s cluster is ready"

# Add Bitnami helm repository
echo "Adding Bitnami helm repository..."
helm repo add bitnami https://charts.bitnami.com/bitnami || true
helm repo update

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

# Create minimal PostgreSQL values file if it doesn't exist
mkdir -p /opt/k8s/configs/postgresql
cat > /opt/k8s/configs/postgresql/values.yaml << 'EOF'
# Minimal PostgreSQL configuration - NO ServiceMonitor components
auth:
  enablePostgresUser: true
  database: "appdb"
primary:
  persistence:
    enabled: true
    size: 10Gi
    storageClass: local-path
  service:
    type: NodePort
    nodePorts:
      postgresql: 30432
# Completely disable all metrics and monitoring components to avoid CRD dependencies
metrics:
  enabled: false
  serviceMonitor:
    enabled: false
  prometheusRule:
    enabled: false
EOF

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
  --values /opt/k8s/configs/postgresql/values.yaml \
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

# Install PostgreSQL Exporter for Prometheus monitoring (simplified, no ServiceMonitor)
echo "Installing PostgreSQL Exporter..."
cat > /opt/k8s/manifests/postgres-exporter.yaml << 'EOF'
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
          value: "postgresql://postgres:$(POSTGRES_PASSWORD)@postgresql.database.svc.cluster.local:5432/appdb?sslmode=disable"
        envFrom:
        - secretRef:
            name: postgres-secret
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

kubectl apply -f /opt/k8s/manifests/postgres-exporter.yaml

# Wait for postgres-exporter to be ready
echo "Waiting for PostgreSQL Exporter to be ready..."
kubectl wait --for=condition=ready pod -l app=postgres-exporter -n database --timeout=300s

# Verify postgres-exporter is responding
echo "Verifying PostgreSQL Exporter is responding..."
sleep 10

# Test if the exporter is accessible locally
for i in {1..10}; do
    if kubectl exec -n database deployment/postgres-exporter -- wget -q -O- http://localhost:9187/metrics | head -5; then
        echo "✅ PostgreSQL Exporter is responding correctly"
        break
    else
        echo "Attempt $i/10: PostgreSQL Exporter not ready, waiting 10 seconds..."
        sleep 10
    fi
done

# Test external access via NodePort
PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/private-ipv4 2>/dev/null || echo "localhost")
echo "Testing PostgreSQL Exporter external access on $PRIVATE_IP:30187..."
sleep 5

# Test NodePort access
if curl -f -m 10 "http://$PRIVATE_IP:30187/metrics" | head -5; then
    echo "✅ PostgreSQL Exporter accessible via NodePort 30187"
else
    echo "⚠️  Warning: PostgreSQL Exporter NodePort access test failed"
    echo "   This may be normal due to security group restrictions"
    echo "   Monitoring instance should still be able to access it"
fi

# Get instance private IP
PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/private-ipv4 2>/dev/null || echo "unknown")

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
