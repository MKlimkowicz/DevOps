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

# Set up k3s log rotation
cat > /etc/logrotate.d/k3s << 'EOF'
/var/log/k3s.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
}
EOF

echo "k3s installation completed successfully"
