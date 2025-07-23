#!/bin/bash

# Script to update Kubernetes secrets
# Usage: ./scripts/update-secrets.sh [environment]

set -e

ENVIRONMENT=${1:-production}
NAMESPACE="devpocket-prod"

echo "🔐 Updating Kubernetes secrets for $ENVIRONMENT environment..."

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

# Function to base64 encode safely
b64encode() {
    echo -n "$1" | base64 -w 0
}

# Prompt for secrets if not provided as environment variables
if [[ -z "$SECRET_KEY" ]]; then
    echo -n "Enter SECRET_KEY (leave empty to generate): "
    read -r SECRET_KEY
    if [[ -z "$SECRET_KEY" ]]; then
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
        echo "Generated new SECRET_KEY"
    fi
fi

if [[ -z "$MONGODB_URL" ]]; then
    echo -n "Enter MONGODB_URL: "
    read -r MONGODB_URL
fi

if [[ -z "$REDIS_URL" ]]; then
    echo -n "Enter REDIS_URL: "
    read -r REDIS_URL
fi

if [[ -z "$GOOGLE_CLIENT_ID" ]]; then
    echo -n "Enter GOOGLE_CLIENT_ID (optional): "
    read -r GOOGLE_CLIENT_ID
fi

if [[ -z "$GOOGLE_CLIENT_SECRET" ]]; then
    echo -n "Enter GOOGLE_CLIENT_SECRET (optional): "
    read -r GOOGLE_CLIENT_SECRET
fi

# Create or update the secret
kubectl create secret generic devpocket-secrets \
    --namespace="$NAMESPACE" \
    --from-literal=SECRET_KEY="$SECRET_KEY" \
    --from-literal=MONGODB_URL="$MONGODB_URL" \
    --from-literal=REDIS_URL="$REDIS_URL" \
    --from-literal=GOOGLE_CLIENT_ID="$GOOGLE_CLIENT_ID" \
    --from-literal=GOOGLE_CLIENT_SECRET="$GOOGLE_CLIENT_SECRET" \
    --dry-run=client -o yaml | kubectl apply -f -

echo "✅ Secrets updated successfully!"
echo "🔄 You may need to restart the deployment for changes to take effect:"
echo "   kubectl rollout restart deployment/devpocket-server -n $NAMESPACE"