#!/bin/bash
set -e
sudo apt-get update -y
sudo apt-get install -y docker.io
sudo systemctl enable --now docker
sudo usermod -aG docker ubuntu

# Create Prometheus config directory
sudo mkdir -p /opt/prometheus
cat <<'EOF' | sudo tee /opt/prometheus/prometheus.yml
scrape_configs:
  - job_name: 'psql-node'
    static_configs:
      - targets: ['${psql_private_ip}:9100']
EOF

# Run Prometheus container
sudo docker run -d \
  --name prometheus \
  --restart unless-stopped \
  -p 9090:9090 \
  -v /opt/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus:latest

# Run Grafana container
sudo docker run -d \
  --name grafana \
  --restart unless-stopped \
  -p 3000:3000 \
  grafana/grafana:latest 