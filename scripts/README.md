# DevPocket Scripts

This directory contains utility scripts for managing the DevPocket server.

## Database Scripts

### reset_collections.py
Interactive script to reset selected database collections with safety confirmations.

**Features:**
- ✅ Interactive selection of collections to reset
- ✅ Safety confirmations for critical collections (users, templates, clusters)
- ✅ Statistics display before deletion
- ✅ Automatic index recreation after reset
- ✅ Support for different environments via ENV_FILE

**Usage:**
```bash
# Development environment
python scripts/reset_collections.py

# Production environment (be very careful!)
ENV_FILE=.env.prod python scripts/reset_collections.py
```

**Available Collections:**
- `environments` - Development environments and their data (safe to reset)
- `sessions` - WebSocket and user sessions (safe to reset)
- `environment_metrics` - Environment usage metrics and logs (safe to reset)
- `users` - User accounts and authentication data (⚠️ DESTRUCTIVE)
- `templates` - Environment templates (⚠️ Will remove custom templates)
- `clusters` - Kubernetes cluster configurations (⚠️ CRITICAL)

**Safety Features:**
- Double confirmation for critical collections
- Document count display before deletion
- Environment and database name verification
- Graceful error handling and rollback

### seed_templates.py
Seeds the database with default environment templates.

**Usage:**
```bash
# Development
python scripts/seed_templates.py

# Production
ENV_FILE=.env.prod python scripts/seed_templates.py

# Force reseed (removes existing templates first)
python scripts/seed_templates.py --force
```

### add_default_ovh_cluster.py
Adds default OVH cluster configuration to the database.

**Usage:**
```bash
# Development
python scripts/add_default_ovh_cluster.py

# Production
ENV_FILE=.env.prod python scripts/add_default_ovh_cluster.py
```

## Development Scripts

### show_default_templates.py
Displays available default templates without requiring database connection.

**Usage:**
```bash
python scripts/show_default_templates.py
```

## Deployment Scripts

### deploy.sh
Automated deployment script for production environments.

### update-secrets.sh
Updates Kubernetes secrets for production deployment.

### get-version.sh
Gets the current version from pyproject.toml.

## Testing Scripts

### run-tests.sh
Runs the test suite with proper environment setup.

**Usage:**
```bash
./scripts/run-tests.sh
```

## Environment Variables

Most scripts support different environments via the `ENV_FILE` environment variable:

```bash
# Use development config (default)
python scripts/script_name.py

# Use production config
ENV_FILE=.env.prod python scripts/script_name.py

# Use custom config file
ENV_FILE=.env.staging python scripts/script_name.py
```

## Safety Guidelines

When working with production databases:

1. **Always verify** the target database name and URL before proceeding
2. **Use ENV_FILE=.env.prod** explicitly for production operations
3. **Take backups** before running destructive operations
4. **Test scripts** in development environment first
5. **Read all confirmations** carefully before typing 'yes' or 'DELETE'

## Common Scenarios

### Reset Development Environment
```bash
# Reset environments and sessions only (safe)
python scripts/reset_collections.py
# Select: 1,2 (environments, sessions)
```

### Clean Test Data
```bash
# Reset environments, sessions, and metrics
python scripts/reset_collections.py
# Select: 1,2,3
```

### Fresh Database Setup
```bash
# Reset all collections (destructive!)
python scripts/reset_collections.py
# Select: 7 (all)

# Reseed templates
python scripts/seed_templates.py

# Add default cluster
python scripts/add_default_ovh_cluster.py
```

### Production Maintenance
```bash
# Reset only sessions and metrics (safe for production)
ENV_FILE=.env.prod python scripts/reset_collections.py
# Select: 2,3 (sessions, environment_metrics)
```