#!/bin/bash
set -e

PROJECT_NAME=$1
ENVIRONMENT=$2
INSTANCE_NAME=$3

echo "Configuring Prometheus for $INSTANCE_NAME instance..."

# Wait for Prometheus to be ready
sleep 30

# Create additional Prometheus configuration for custom targets
cat > /opt/k8s/manifests/prometheus-additional-config.yaml << 'EOF'
apiVersion: v1
kind: Secret
metadata:
  name: additional-scrape-configs
  namespace: monitoring
stringData:
  prometheus-additional.yaml: |
    - job_name: 'node-exporter-external'
      static_configs:
        - targets: ['localhost:9100']
      scrape_interval: 30s
      metrics_path: /metrics
    
    - job_name: 'custom-app-metrics'
      static_configs:
        - targets: ['localhost:8080']
      scrape_interval: 30s
      metrics_path: /metrics
      scrape_timeout: 10s
EOF

kubectl apply -f /opt/k8s/manifests/prometheus-additional-config.yaml

# Update Prometheus configuration to include additional scrape configs
kubectl patch prometheus kube-prometheus-stack-prometheus -n monitoring --type='merge' -p='{"spec":{"additionalScrapeConfigs":{"name":"additional-scrape-configs","key":"prometheus-additional.yaml"}}}'

# Create PrometheusRule for custom alerting rules
cat > /opt/k8s/manifests/custom-prometheus-rules.yaml << 'EOF'
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: custom-infrastructure-rules
  namespace: monitoring
  labels:
    prometheus: kube-prometheus-stack-prometheus
    role: alert-rules
spec:
  groups:
  - name: infrastructure.rules
    rules:
    - alert: HighCPUUsage
      expr: 100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High CPU usage detected"
        description: "CPU usage is above 80% for more than 5 minutes on {{ $labels.instance }}"
    
    - alert: HighMemoryUsage
      expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 85
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High memory usage detected"
        description: "Memory usage is above 85% for more than 5 minutes on {{ $labels.instance }}"
    
    - alert: DiskSpaceLow
      expr: (1 - (node_filesystem_avail_bytes{fstype!="tmpfs"} / node_filesystem_size_bytes{fstype!="tmpfs"})) * 100 > 90
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "Disk space is running low"
        description: "Disk usage is above 90% on {{ $labels.instance }} filesystem {{ $labels.mountpoint }}"
    
    - alert: PostgreSQLDown
      expr: up{job="postgres-exporter"} == 0
      for: 2m
      labels:
        severity: critical
      annotations:
        summary: "PostgreSQL is down"
        description: "PostgreSQL database is not responding"
EOF

kubectl apply -f /opt/k8s/manifests/custom-prometheus-rules.yaml

# Create ServiceMonitor for node-exporter on this instance
cat > /opt/k8s/manifests/node-exporter-servicemonitor.yaml << 'EOF'
apiVersion: v1
kind: Service
metadata:
  name: node-exporter-external
  namespace: monitoring
  labels:
    app: node-exporter-external
spec:
  ports:
  - port: 9100
    targetPort: 9100
    name: metrics
  type: ExternalName
  externalName: localhost
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: node-exporter-external
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: node-exporter-external
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
EOF

kubectl apply -f /opt/k8s/manifests/node-exporter-servicemonitor.yaml

# Install and configure node-exporter as a systemd service
curl -LO https://github.com/prometheus/node_exporter/releases/download/v1.6.1/node_exporter-1.6.1.linux-amd64.tar.gz
tar xvf node_exporter-1.6.1.linux-amd64.tar.gz
sudo cp node_exporter-1.6.1.linux-amd64/node_exporter /usr/local/bin/
rm -rf node_exporter-1.6.1.linux-amd64*

# Create node-exporter systemd service
cat > /etc/systemd/system/node-exporter.service << 'EOF'
[Unit]
Description=Node Exporter
After=network.target

[Service]
User=nobody
Group=nobody
Type=simple
ExecStart=/usr/local/bin/node_exporter --web.listen-address=:9100
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable node-exporter
systemctl start node-exporter

echo "Prometheus configuration completed successfully"
echo "Node Exporter is running on port 9100"
echo "Custom alerting rules have been applied"
