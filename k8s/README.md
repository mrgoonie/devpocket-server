# Kubernetes Deployment Guide

This directory contains Kubernetes manifests for deploying DevPocket Server to production.

## Prerequisites

- Kubernetes cluster with kubectl configured
- Docker registry access for `digitop/devpocket-api`
- Ingress controller (nginx) installed in cluster
- cert-manager for TLS certificates (optional)

## Deployment Files

- `namespace.yaml` - Creates the production namespace
- `configmap.yaml` - Application configuration and secrets template
- `deployment.yaml` - Main application deployment
- `service.yaml` - Service and Ingress configuration
- `hpa.yaml` - Horizontal Pod Autoscaler

## Quick Deployment

### Automated (via GitHub Actions)
Pushes to `main` branch automatically trigger deployment via the GitHub Actions workflow.

### Manual Deployment
```bash
# Deploy with latest version
./scripts/deploy.sh

# Deploy specific version
./scripts/deploy.sh v1.2.3
```

### Update Secrets
```bash
./scripts/update-secrets.sh
```

## Environment Variables

### Configuration (ConfigMap)
- `APP_NAME` - Application name
- `ENVIRONMENT` - Runtime environment (production)
- `DEBUG` - Debug mode (false for production)
- `HOST` - Bind host (0.0.0.0)
- `PORT` - Application port (8000)
- `DATABASE_NAME` - MongoDB database name
- `LOG_LEVEL` - Logging level (INFO)
- `LOG_FORMAT` - Log format (json)

### Secrets
- `SECRET_KEY` - JWT signing key
- `MONGODB_URL` - MongoDB connection string
- `REDIS_URL` - Redis connection string
- `GOOGLE_CLIENT_ID` - Google OAuth client ID (optional)
- `GOOGLE_CLIENT_SECRET` - Google OAuth client secret (optional)

## Ingress Configuration

Update the following in `service.yaml`:
- Replace `api.devpocket.io` with your actual domain
- Configure TLS certificate if using cert-manager

## Monitoring

### Check Deployment Status
```bash
kubectl get pods -n devpocket-prod -l app=devpocket-server
kubectl get svc -n devpocket-prod
kubectl get ingress -n devpocket-prod
```

### View Logs
```bash
kubectl logs -n devpocket-prod -l app=devpocket-server -f
```

### Check Health
```bash
kubectl exec -n devpocket-prod deployment/devpocket-server -- curl -f http://localhost:8000/health
```

## Scaling

The deployment includes a Horizontal Pod Autoscaler (HPA) that:
- Maintains 3-10 replicas
- Scales based on CPU (70%) and memory (80%) usage
- Has intelligent scaling policies to prevent flapping

Manual scaling:
```bash
kubectl scale deployment devpocket-server --replicas=5 -n devpocket-prod
```

## Troubleshooting

### Pod Issues
```bash
# Describe pod for events
kubectl describe pod -n devpocket-prod -l app=devpocket-server

# Check resource usage
kubectl top pods -n devpocket-prod
```

### Service Issues
```bash
# Test service connectivity
kubectl exec -n devpocket-prod deployment/devpocket-server -- wget -qO- http://devpocket-server-service/health

# Check endpoints
kubectl get endpoints -n devpocket-prod devpocket-server-service
```

### Ingress Issues
```bash
# Check ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx

# Test internal connectivity
kubectl run test-pod --rm -i --tty --image=nginx -- /bin/bash
# From within: curl http://devpocket-server-service.devpocket-prod.svc.cluster.local/health
```

## Security Notes

- Pods run as non-root user (UID 1000)
- Read-only root filesystem disabled for application needs
- Resource limits enforced
- Secrets are stored in Kubernetes secrets (base64 encoded)
- Network policies can be added for additional security

## Updates

The GitHub Actions workflow automatically:
1. Builds multi-architecture Docker images
2. Tags with semantic version
3. Deploys to Kubernetes
4. Creates Git tags
5. Runs health checks

For manual updates, use the deployment script with a specific version tag.
