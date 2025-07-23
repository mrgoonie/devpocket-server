# Multi-Cluster Support Implementation

## Status: In Progress

## Tasks:

- [x] Check if kube_config is stored in database (not implemented)
- [ ] Create cluster model with kube_config storage
- [ ] Update user model to include preferred_region
- [ ] Create cluster management service
- [ ] Add cluster endpoints for admin
- [ ] Update environment service to use selected cluster
- [ ] Add region selection in user registration/settings
- [ ] Update frontend to show available regions

## Implementation Details:

1. **Cluster Model**: Store cluster information including name, region, kube_config, and status
2. **User Model**: Add preferred_region field to user preferences
3. **Environment Service**: Route environment creation to appropriate cluster based on user region
4. **Admin Endpoints**: Allow admins to add/remove clusters
5. **Security**: Encrypt kube_config data in database