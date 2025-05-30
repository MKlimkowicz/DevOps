#!/bin/bash

echo "🔐 Setting up secure configuration for DevOps Infrastructure..."

# Get user's public IP
echo "📡 Getting your public IP address..."
PUBLIC_IP=$(curl -s ifconfig.me)

if [ -z "$PUBLIC_IP" ]; then
    echo "❌ Failed to get public IP. Please check your internet connection."
    exit 1
fi

echo "✅ Your public IP: $PUBLIC_IP"

# Create terraform.tfvars from example if it doesn't exist
if [ ! -f "terraform.tfvars" ]; then
    echo "📝 Creating terraform.tfvars from example..."
    cp terraform.tfvars.example terraform.tfvars
fi

# Update the IP addresses in terraform.tfvars
echo "🔧 Updating security configuration..."
sed -i.bak "s/YOUR_PUBLIC_IP/$PUBLIC_IP/g" terraform.tfvars

echo "✅ Configuration updated successfully!"
echo ""
echo "🔐 Security settings:"
echo "   - ALB access restricted to: $PUBLIC_IP/32"
echo "   - SSH access restricted to: $PUBLIC_IP/32"
echo ""
echo "🚀 You can now deploy with:"
echo "   terraform init"
echo "   terraform apply"
echo ""
echo "💡 If your IP changes, run this script again to update the configuration." 