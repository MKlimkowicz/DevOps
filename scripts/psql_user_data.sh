#!/bin/bash
set -e
# Update and install Docker
sudo apt-get update -y
sudo apt-get install -y docker.io
sudo systemctl enable --now docker
# Allow ubuntu user to run docker
sudo usermod -aG docker ubuntu
# Pull and run Node Exporter container
sudo docker run -d \
  --name node_exporter \
  --restart unless-stopped \
  -p 9100:9100 \
  prom/node-exporter:latest
# Pull and run PostgreSQL container
sudo docker run -d \
  --name postgres \
  --restart unless-stopped \
  -e POSTGRES_USER=admin \
  -e POSTGRES_PASSWORD=secretpassword \
  -e POSTGRES_DB=metrics \
  -p 5432:5432 \
  postgres:15-alpine 