#!/bin/bash
set -e

PROJECT_NAME=$1
ENVIRONMENT=$2
INSTANCE_NAME=$3

echo "Setting up PostgreSQL database on $INSTANCE_NAME instance..."

# Wait for k3s to be ready
sleep 60

# Get PostgreSQL password from Parameter Store
# Get region with fallback and debugging
echo "DEBUG: Getting region from metadata..."
AZ=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
echo "DEBUG: Availability Zone: $AZ"
if [ -n "$AZ" ]; then
    REGION=$(echo "$AZ" | sed 's/[a-z]$//')
else
    # Fallback to eu-central-1 if metadata fails
    REGION="eu-central-1"
fi
echo "DEBUG: Using region: $REGION"

POSTGRES_PASSWORD=$(aws ssm get-parameter --name "/$PROJECT_NAME/$ENVIRONMENT/postgres/password" --with-decryption --query 'Parameter.Value' --output text --region "$REGION")

# Create database namespace
kubectl create namespace database || true

# Create secret for PostgreSQL password
kubectl create secret generic postgres-secret \
  --from-literal=postgres-password="$POSTGRES_PASSWORD" \
  --namespace database || true

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
  --set metrics.serviceMonitor.namespace=monitoring \
  --values /opt/k8s/configs/postgresql/values.yaml || true

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgresql -n database --timeout=300s

# Create a sample database and table
sleep 30

# Get the PostgreSQL pod name
POSTGRES_POD=$(kubectl get pods -n database -l app.kubernetes.io/name=postgresql -o jsonpath='{.items[0].metadata.name}')

# Create sample data
kubectl exec -n database "$POSTGRES_POD" -- psql -U postgres -d appdb -c "
CREATE TABLE IF NOT EXISTS sample_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metric_name VARCHAR(100),
    metric_value FLOAT,
    instance_id VARCHAR(50)
);

INSERT INTO sample_metrics (metric_name, metric_value, instance_id) VALUES
('cpu_usage', 45.2, 'i-1234567890abcdef0'),
('memory_usage', 67.8, 'i-1234567890abcdef0'),
('disk_usage', 23.1, 'i-1234567890abcdef0');
"

# Install PostgreSQL Exporter for Prometheus monitoring
cat > /opt/k8s/manifests/postgres-exporter.yaml << 'EOF'
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
        image: prometheuscommunity/postgres-exporter:latest
        ports:
        - containerPort: 9187
        env:
        - name: DATA_SOURCE_NAME
          value: "postgresql://postgres:$(POSTGRES_PASSWORD)@postgresql:5432/appdb?sslmode=disable"
        envFrom:
        - secretRef:
            name: postgres-secret
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
    name: metrics
  selector:
    app: postgres-exporter
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: postgres-exporter
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: postgres-exporter
  namespaceSelector:
    matchNames:
    - database
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
EOF

kubectl apply -f /opt/k8s/manifests/postgres-exporter.yaml

echo "PostgreSQL database setup completed successfully"
echo "PostgreSQL will be available at: $(curl -s http://169.254.169.254/latest/meta-data/private-ipv4):30432"
echo "Database: appdb"
echo "Username: postgres"
echo "Password stored in Parameter Store: /$PROJECT_NAME/$ENVIRONMENT/postgres/password"
