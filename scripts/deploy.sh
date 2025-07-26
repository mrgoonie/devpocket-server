#!/bin/bash

# Manual deployment script for DevPocket Server
# Usage: ./scripts/deploy.sh [version]

set -e

VERSION=${1:-latest}
NAMESPACE="devpocket-prod"
IMAGE_NAME="digitop/devpocket-api:$VERSION"

echo "🚀 Deploying DevPocket Server..."
echo "📦 Image: $IMAGE_NAME"
echo "🎯 Namespace: $NAMESPACE"
echo "📝 Version: $VERSION"
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed or not in PATH"
    exit 1
fi

# Check if we can connect to the cluster
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster. Check your kubeconfig."
    exit 1
fi

echo "✅ Connected to Kubernetes cluster"

# Create namespace if it doesn't exist
echo "🏗️  Creating namespace..."
kubectl apply -f k8s/namespace.yaml

# Apply ConfigMaps and Secrets
echo "⚙️  Applying configuration..."
kubectl apply -f k8s/configmap.yaml

# Update deployment with new image
echo "🔄 Updating deployment image to $IMAGE_NAME..."
sed -i.bak "s|image: digitop/devpocket-api:.*|image: $IMAGE_NAME|g" k8s/deployment.yaml
sed -i.bak "s|version: .*|version: $VERSION|g" k8s/deployment.yaml

# Apply deployment
echo "📦 Applying deployment..."
kubectl apply -f k8s/deployment.yaml

# Apply services and ingress
echo "🌐 Applying services..."
kubectl apply -f k8s/service.yaml

# Apply HPA
echo "📈 Applying horizontal pod autoscaler..."
kubectl apply -f k8s/hpa.yaml

# Wait for rollout to complete
echo "⏳ Waiting for deployment to complete..."
kubectl rollout status deployment/devpocket-server -n $NAMESPACE --timeout=600s

# Restore original deployment file
mv k8s/deployment.yaml.bak k8s/deployment.yaml

# Show deployment status
echo ""
echo "📊 Deployment Status:"
kubectl get pods -n $NAMESPACE -l app=devpocket-server -o wide

echo ""
echo "🌐 Services:"
kubectl get svc -n $NAMESPACE

echo ""
echo "📡 Ingress:"
kubectl get ingress -n $NAMESPACE

echo ""
echo "🎉 Deployment completed successfully!"
echo "🔍 To check logs: kubectl logs -n $NAMESPACE -l app=devpocket-server -f"
echo "📊 To check status: kubectl get pods -n $NAMESPACE -l app=devpocket-server"
