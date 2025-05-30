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

# Configure Grafana datasources and dashboards
sleep 30

# Create custom dashboard for infrastructure monitoring
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
        "tags": ["infrastructure"],
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
            ]
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
