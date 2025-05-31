#!/bin/bash
set -e

PROJECT_NAME=$1
ENVIRONMENT=$2
INSTANCE_NAME=$3

echo "Setting up monitoring stack on $INSTANCE_NAME instance..."

# Wait for k3s to be ready
sleep 60

# Get Grafana password from Parameter Store
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

GRAFANA_PASSWORD=$(aws ssm get-parameter --name "/$PROJECT_NAME/$ENVIRONMENT/grafana/admin-password" --with-decryption --query 'Parameter.Value' --output text --region "$REGION")

# Create monitoring namespace
kubectl create namespace monitoring || true

# Create secret for Grafana admin password
kubectl create secret generic grafana-admin-secret \
  --from-literal=admin-password="$GRAFANA_PASSWORD" \
  --namespace monitoring || true

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
  --values /opt/k8s/configs/prometheus/values.yaml || true

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
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=grafana -n monitoring --timeout=300s
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=prometheus -n monitoring --timeout=300s

# Configure cross-instance PostgreSQL monitoring
echo "Setting up PostgreSQL monitoring from database instance..."

# Get database instance private IP if database is deployed
if [ "$INSTANCE_NAME" = "monitoring" ]; then
    echo "Retrieving database instance IP from Parameter Store..."
    DATABASE_IP=$(aws ssm get-parameter --name "/$PROJECT_NAME/$ENVIRONMENT/database/private-ip" --query 'Parameter.Value' --output text --region "$REGION" 2>/dev/null || echo "")
    
    if [ -n "$DATABASE_IP" ]; then
        echo "Database instance IP: $DATABASE_IP"
        
        # Wait for database instance to be ready (postgres-exporter on port 30187)
        echo "Waiting for PostgreSQL exporter to be available on database instance..."
        for i in {1..30}; do
            if curl -f -m 5 "http://$DATABASE_IP:30187/metrics" >/dev/null 2>&1; then
                echo "PostgreSQL exporter is responding on database instance"
                break
            fi
            echo "Attempt $i/30: PostgreSQL exporter not ready, waiting 10 seconds..."
            sleep 10
        done
        
        # Create ServiceMonitor for remote PostgreSQL exporter
        cat > /opt/k8s/manifests/postgres-servicemonitor.yaml << EOF
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: postgres-external
  namespace: monitoring
  labels:
    app: postgres-exporter
    release: kube-prometheus-stack
spec:
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
    targetPort: 30187
  namespaceSelector:
    matchNames:
    - monitoring
  selector:
    matchLabels:
      app: postgres-external
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-external
  namespace: monitoring
  labels:
    app: postgres-external
spec:
  type: ExternalName
  externalName: ${DATABASE_IP}
  ports:
  - port: 30187
    targetPort: 30187
    name: metrics
---
apiVersion: v1
kind: Endpoints
metadata:
  name: postgres-external
  namespace: monitoring
subsets:
- addresses:
  - ip: ${DATABASE_IP}
  ports:
  - name: metrics
    port: 30187
    protocol: TCP
EOF
        
        # Wait for Prometheus Operator to be ready before applying ServiceMonitor
        echo "Waiting for Prometheus Operator to be ready..."
        kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=prometheus-operator -n monitoring --timeout=300s
        
        # Apply the ServiceMonitor configuration
        kubectl apply -f /opt/k8s/manifests/postgres-servicemonitor.yaml
        echo "✅ PostgreSQL monitoring configured for database at $DATABASE_IP"
        
        # Verify ServiceMonitor was created successfully
        kubectl get servicemonitor postgres-external -n monitoring >/dev/null 2>&1 && \
            echo "✅ ServiceMonitor postgres-external created successfully" || \
            echo "⚠️  Warning: ServiceMonitor creation may have failed"
            
    else
        echo "⚠️  Database instance IP not found - skipping PostgreSQL monitoring setup"
        echo "   This is normal if database instance is not deployed or not ready yet"
        echo "   PostgreSQL monitoring can be configured later manually"
    fi
fi

# Configure Grafana datasources and dashboards
sleep 30

# Create PostgreSQL dashboard for Grafana
cat > /opt/k8s/manifests/postgresql-dashboard.yaml << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: postgresql-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  postgresql.json: |
    {
      "dashboard": {
        "id": null,
        "title": "PostgreSQL Database Metrics",
        "tags": ["postgresql", "database"],
        "timezone": "browser",
        "panels": [
          {
            "id": 1,
            "title": "Database Connections",
            "type": "stat",
            "targets": [
              {
                "expr": "pg_stat_database_numbackends{datname=\"appdb\"}",
                "legendFormat": "Active Connections"
              }
            ],
            "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0}
          },
          {
            "id": 2,
            "title": "Database Size",
            "type": "stat",
            "targets": [
              {
                "expr": "pg_database_size_bytes{datname=\"appdb\"} / 1024 / 1024",
                "legendFormat": "Size (MB)"
              }
            ],
            "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0}
          },
          {
            "id": 3,
            "title": "Queries per Second",
            "type": "graph",
            "targets": [
              {
                "expr": "rate(pg_stat_database_tup_inserted{datname=\"appdb\"}[5m])",
                "legendFormat": "Inserts/sec"
              },
              {
                "expr": "rate(pg_stat_database_tup_updated{datname=\"appdb\"}[5m])",
                "legendFormat": "Updates/sec"
              },
              {
                "expr": "rate(pg_stat_database_tup_deleted{datname=\"appdb\"}[5m])",
                "legendFormat": "Deletes/sec"
              }
            ],
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
          },
          {
            "id": 4,
            "title": "Sample Metrics Table Data",
            "type": "table",
            "targets": [
              {
                "expr": "pg_stat_user_tables_n_tup_ins{relname=\"sample_metrics\"}",
                "legendFormat": "Records Inserted",
                "format": "table"
              }
            ],
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16}
          }
        ],
        "time": {
          "from": "now-1h",
          "to": "now"
        },
        "refresh": "10s"
      }
    }
EOF

kubectl apply -f /opt/k8s/manifests/postgresql-dashboard.yaml

# Create infrastructure dashboard for general monitoring
cat > /opt/k8s/manifests/infrastructure-dashboard.yaml << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: infrastructure-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  infrastructure.json: |
    {
      "dashboard": {
        "id": null,
        "title": "Infrastructure Overview",
        "tags": ["infrastructure", "kubernetes"],
        "timezone": "browser",
        "panels": [
          {
            "id": 1,
            "title": "CPU Usage",
            "type": "graph",
            "targets": [
              {
                "expr": "100 - (avg by (instance) (irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
                "legendFormat": "{{instance}}"
              }
            ],
            "yAxes": [
              {
                "min": 0,
                "max": 100,
                "unit": "percent"
              }
            ],
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
          },
          {
            "id": 2,
            "title": "Memory Usage",
            "type": "graph",
            "targets": [
              {
                "expr": "((node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes) * 100",
                "legendFormat": "{{instance}}"
              }
            ],
            "yAxes": [
              {
                "min": 0,
                "max": 100,
                "unit": "percent"
              }
            ],
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
          }
        ],
        "time": {
          "from": "now-1h",
          "to": "now"
        },
        "refresh": "5s"
      }
    }
EOF

kubectl apply -f /opt/k8s/manifests/infrastructure-dashboard.yaml

echo "Monitoring stack setup completed successfully"
echo "Grafana will be available at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):30003"
echo "Prometheus will be available at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):30001"
