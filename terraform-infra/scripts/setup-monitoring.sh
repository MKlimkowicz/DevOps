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
REGION=$(echo "$AZ" | sed 's/[a-z]$//' || echo "eu-central-1")

GRAFANA_PASSWORD=$(aws ssm get-parameter --name "/$PROJECT_NAME/$ENVIRONMENT/grafana/admin-password" --with-decryption --query 'Parameter.Value' --output text --region "$REGION")

# Create monitoring namespace
kubectl create namespace monitoring || true

# Install kube-prometheus-stack
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
  --set grafana.sidecar.datasources.enabled=true \
  --set grafana.sidecar.dashboards.enabled=true \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
  --set prometheus.prometheusSpec.ruleSelectorNilUsesHelmValues=false

# Create additional Grafana service for ALB
cat > /tmp/grafana-service.yaml << 'EOF'
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

kubectl apply -f /tmp/grafana-service.yaml

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=grafana -n monitoring --timeout=300s || true
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=prometheus -n monitoring --timeout=300s || true

# Check for database instance
DATABASE_INSTANCE_IP=""
for i in {1..60}; do
    if DATABASE_INSTANCE_IP=$(aws ssm get-parameter --name "/$PROJECT_NAME/$ENVIRONMENT/database/private-ip" --query 'Parameter.Value' --output text --region "$REGION" 2>/dev/null); then
        if [ -n "$DATABASE_INSTANCE_IP" ] && [ "$DATABASE_INSTANCE_IP" != "None" ]; then
            echo "Database instance detected at IP: $DATABASE_INSTANCE_IP"
            break
        fi
    fi
    echo "Attempt $i/60: Waiting for database instance IP..."
    sleep 10
done

if [ -n "$DATABASE_INSTANCE_IP" ] && [ "$DATABASE_INSTANCE_IP" != "None" ]; then
    echo "Setting up monitoring for database instance at $DATABASE_INSTANCE_IP..."
    
    # Test connectivity
    NODE_EXPORTER_OK=false
    POSTGRES_EXPORTER_OK=false
    
    if timeout 10 curl -f -s "http://$DATABASE_INSTANCE_IP:30100/metrics" > /dev/null; then
        echo "✅ Node Exporter accessible"
        NODE_EXPORTER_OK=true
    fi
    
    if timeout 10 curl -f -s "http://$DATABASE_INSTANCE_IP:30187/metrics" > /dev/null; then
        PG_UP=$(timeout 10 curl -s "http://$DATABASE_INSTANCE_IP:30187/metrics" | grep "pg_up" | head -1 | awk '{print $2}' || echo "0")
        if [ "$PG_UP" = "1" ]; then
            echo "✅ PostgreSQL Exporter accessible and connected"
            POSTGRES_EXPORTER_OK=true
        fi
    fi
    
    # Configure cross-instance monitoring if exporters are accessible
    if [ "$NODE_EXPORTER_OK" = "true" ] || [ "$POSTGRES_EXPORTER_OK" = "true" ]; then
        cat > /tmp/database-monitoring.yaml << EOF
apiVersion: v1
kind: Secret
metadata:
  name: additional-scrape-configs
  namespace: monitoring
stringData:
  prometheus-additional.yaml: |
    - job_name: 'database-node-exporter'
      static_configs:
        - targets: ['$DATABASE_INSTANCE_IP:30100']
          labels:
            instance_type: 'database'
            environment: '$ENVIRONMENT'
      scrape_interval: 30s
      
    - job_name: 'database-postgres-exporter'
      static_configs:
        - targets: ['$DATABASE_INSTANCE_IP:30187']
          labels:
            instance_type: 'database'
            environment: '$ENVIRONMENT'
      scrape_interval: 30s
EOF
        
        kubectl apply -f /tmp/database-monitoring.yaml
        kubectl patch prometheus kube-prometheus-stack-prometheus -n monitoring --type='merge' -p='{"spec":{"additionalScrapeConfigs":{"name":"additional-scrape-configs","key":"prometheus-additional.yaml"}}}'
        echo "✅ Cross-instance monitoring configured"
    else
        echo "❌ No database exporters accessible"
    fi
else
    echo "⚠️ Database instance IP not found"
fi

echo "Monitoring stack setup completed successfully"
