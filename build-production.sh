#!/bin/bash

# Production Build Script for DevPocket Server
# Ensures consistent cross-platform builds

set -e

echo "🏗️  Building DevPocket Server for production..."

# Check if we're building for a specific registry
REGISTRY=${1:-"devpocket"}
IMAGE_NAME="${REGISTRY}/api"
VERSION=${2:-"latest"}

echo "📦 Building image: ${IMAGE_NAME}:${VERSION}"
echo "🎯 Target platform: linux/amd64"

# Build the image for production (x86_64/amd64)
docker build \
    --platform linux/amd64 \
    --build-arg ENVIRONMENT=production \
    -t "${IMAGE_NAME}:${VERSION}" \
    -t "${IMAGE_NAME}:latest" \
    .

echo "✅ Build completed successfully!"
echo "📋 Image details:"
docker images "${IMAGE_NAME}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

echo ""
echo "🚀 Next steps:"
echo "  1. Push to registry: docker push ${IMAGE_NAME}:${VERSION}"
echo "  2. Update Kubernetes deployment with new image"
echo "  3. Apply deployment: kubectl apply -f k8s/"

# Optional: Push if PUSH=true is set
if [ "$PUSH" = "true" ]; then
    echo "📤 Pushing to registry..."
    docker push "${IMAGE_NAME}:${VERSION}"
    docker push "${IMAGE_NAME}:latest"
    echo "✅ Push completed!"
fi