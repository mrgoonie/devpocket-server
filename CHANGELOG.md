# CHANGELOG


## v0.1.0-dev.1 (2025-07-26)

### Bug Fixes

- Resolve semantic-release build and packaging issues
  ([`c56c0ad`](https://github.com/mrgoonie/devpocket-server/commit/c56c0adfb15277e1503cd03bcf5fd26731bad78c))

- Replace deprecated --dry-run option with --print command approach - Fix pyproject.toml license
  format to use simple string instead of TOML table - Remove deprecated license classifier to avoid
  setuptools warnings - Add package discovery configuration to exclude non-package directories -
  Change build command from editable install to python -m build - Add build dependency to GitHub
  Actions workflow - Resolve 'Multiple top-level packages' error by explicitly including only app
  package

Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>

- Resolve Redis connection timeout in GitHub Actions test workflow
  ([`4103240`](https://github.com/mrgoonie/devpocket-server/commit/41032402a62bb9079469a22ea5bdf426953b44b8))

- Add Redis CLI installation step in GitHub Actions - Implement timeout mechanism (60 seconds) with
  proper error handling - Add container log inspection on Redis connection failure - Mirror the
  MongoDB fix to prevent Redis hanging during tests

Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>

- Resolve GitHub Actions issues and setup pre-commit hooks
  ([`4fc0b7a`](https://github.com/mrgoonie/devpocket-server/commit/4fc0b7a5d7c793f985e30fd9d52fd6c0f8ef52e8))

- Fix MongoDB connection timeout in test workflow with proper shell installation and error handling
  - Resolve code quality checks by formatting all Python files with black - Fix flake8 violations
  including bare except statements and boolean comparisons - Setup comprehensive pre-commit hooks
  for automatic code formatting - Split Kubernetes YAML files to resolve validation issues - Update
  semantic-release workflow to use --dry-run instead of deprecated --noop option - Add pre-commit
  configuration with black, isort, flake8, and file validation hooks

Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>

- Resolve MongoDB ObjectId conversion issues in template operations
  ([`e0873b0`](https://github.com/mrgoonie/devpocket-server/commit/e0873b0008ecf2a111cfc49bdb5495f6fdd4d345))

- Fix get_template_by_id to properly convert string IDs to ObjectId for database queries - Fix
  update_template to handle ObjectId conversion with error handling - Fix delete_template to convert
  string IDs to ObjectId before database operations - Update test_create_duplicate_template_fails to
  create template first before testing duplicates - Update test_admin_can_update_template to create
  template before attempting updates - All template CRUD operations now properly handle MongoDB
  ObjectId requirements

Fixes 4 failing template tests: - test_get_template_by_id - test_create_duplicate_template_fails -
  test_admin_can_update_template - test_admin_can_delete_template

- Update test fixtures and docker compose configuration
  ([`b3e500b`](https://github.com/mrgoonie/devpocket-server/commit/b3e500b523660bcf16a3d152b26b06099cc67419))

- Update pytest fixtures to use pytest_asyncio for proper async fixture handling - Fix HTTP status
  codes in tests (401 -> 403 for unauthorized, add 423 for locked) - Change account lockout status
  to HTTP 423 LOCKED for clarity - Remove deprecated docker-compose version from yaml files -
  Consolidate pytest async mode configuration - Move TEST_STATUS.md to plans directory for better
  organization

- Update CodeQL action from v2 to v3 to fix deprecation warning
  ([`8454efe`](https://github.com/mrgoonie/devpocket-server/commit/8454efe2fa38f994c0196c50a0237907b3872c94))

- Add authentication to MongoDB health check in GitHub Actions
  ([`944f543`](https://github.com/mrgoonie/devpocket-server/commit/944f543d840b33b15e313a7c739c47ae01e69b0d))

- **api**: Support ending slash
  ([`cfb575c`](https://github.com/mrgoonie/devpocket-server/commit/cfb575cfe5e670a1bb8307481ab1699aaa3f72aa))

- **templates**: Add debug logs
  ([`1747dc0`](https://github.com/mrgoonie/devpocket-server/commit/1747dc06752bafbd9e1be57b4154c24a67cc00a3))

- **templates**: Add debug logs
  ([`f5980d3`](https://github.com/mrgoonie/devpocket-server/commit/f5980d39a6917721c85005fbf74699c4663c9a0c))

- **templates**: Add debug logs
  ([`ce6b27d`](https://github.com/mrgoonie/devpocket-server/commit/ce6b27d9673a536d841fb0cc4047bca585404027))

- **templates**: Correct access permissions"
  ([`48fcc0d`](https://github.com/mrgoonie/devpocket-server/commit/48fcc0dab7a1c9ca803f2698cb6bbf9dd5fcb430))

- Resolve templates endpoint filtering issue
  ([`e935c2c`](https://github.com/mrgoonie/devpocket-server/commit/e935c2c874c2ef9e2945d927b21aa0160c8f1a82))

- Fix admin permission check inconsistency in templates filtering - Template listing now correctly
  shows all active templates for pro/admin users - Align filtering logic with admin access
  permissions (pro + admin plans) - Add comprehensive logging for debugging template conversion
  issues - Add error handling for template response conversion failures

Root cause: Template filtering used subscription_plan \!= 'admin' but admin access allows both 'pro'
  and 'admin' plans, causing pro users to see filtered results incorrectly.

- Update GitHub Actions to use docker compose plugin
  ([`c712078`](https://github.com/mrgoonie/devpocket-server/commit/c7120785f7fc23b551873c88c97d35592ccf301b))

- Replace docker-compose command with docker compose - Fixes CI failure due to missing
  docker-compose command in runner

- Allow tests directory in Docker builds
  ([`a533079`](https://github.com/mrgoonie/devpocket-server/commit/a53307927722a9498d4d5e723b8a75b4a00e15e4))

- Comment out test directory exclusions in .dockerignore - Enables test builds to access test files
  properly

- Resolve Docker architecture mismatch and improve build process
  ([`42153d6`](https://github.com/mrgoonie/devpocket-server/commit/42153d603bba750a83f3b3e6b12bdf6a23016379))

- Add explicit linux/amd64 platform specification to fix 'exec format error' - Create production
  build script with consistent cross-platform builds - Fix Dockerfile casing warnings for
  multi-stage builds - Update docker-compose.yaml to include platform specification - Resolves
  deployment errors on x86_64 Kubernetes clusters

- Resolve Pydantic ObjectId validation errors
  ([`7296a20`](https://github.com/mrgoonie/devpocket-server/commit/7296a20e8dd0ffa144143a3a967e41d014b44f09))

- Update PyObjectId class to properly convert ObjectId to string for Pydantic v2 compatibility - Fix
  UserInDB, ClusterInDB, and EnvironmentInDB models to use string type for id fields - Add ObjectId
  conversion helpers in auth_service and middleware - Update database queries to use ObjectId for
  MongoDB while maintaining string types for Pydantic models - Resolves production errors: 'Input
  should be a valid string [type=string_type, input_value=ObjectId(...)]'

### Features

- Improve test infrastructure and environment service reliability
  ([`476ce5d`](https://github.com/mrgoonie/devpocket-server/commit/476ce5d7c472f541cb369a44a9f7bf495c813f3a))

- Add test environment detection and skip rate limiting in tests - Improve MongoDB authentication
  configuration for test environment - Add ObjectId conversion fixes for environment operations -
  Enhance environment service with test mode simulation - Fix readiness check to handle
  uninitialized database client - Update test fixtures to properly seed templates and setup admin
  users - Improve test assertions and error handling across test suites - Add TESTING environment
  variable to control test-specific behavior

This commit consolidates various testing improvements and fixes that ensure reliable test execution
  and proper simulation of production behavior in test mode.

- Implement MongoDB ObjectId migration and database management tools
  ([`dc0f23b`](https://github.com/mrgoonie/devpocket-server/commit/dc0f23bbac3efacc09ddb0c912a53dbc21c27b43))

- Update all database models to use PyObjectId for proper MongoDB ObjectId handling - Add
  SYSTEM_USER_ID constant for system-created items (templates, clusters) - Fix WebSocket
  authentication ObjectId conversion - Create comprehensive database reset script with safety
  features - Update services to handle ObjectId conversion properly - Add extensive documentation
  for database scripts

Core Changes: - Models: UserInDB, EnvironmentInDB, WebSocketSession, ClusterInDB, TemplateInDB now
  use PyObjectId - Services: template_service and cluster_service use SYSTEM_USER_ID - WebSocket:
  Fixed user_id ObjectId conversion in authentication - Constants: Added SYSTEM_USER_ID =
  ObjectId("000000000000000000000001")

Database Tools: - scripts/reset_collections.py: Interactive collection reset with safety
  confirmations - scripts/README.md: Comprehensive documentation for all scripts - Support for
  development and production environments

Test Infrastructure: - Updated test structure to function-based approach - Documented pytest-asyncio
  fixture compatibility issues - Core ObjectId functionality verified and working

The ObjectId migration is complete and functional. Application starts successfully, endpoints
  respond correctly, and database operations work with proper ObjectId types.

- Implement semantic release automation
  ([`693d35d`](https://github.com/mrgoonie/devpocket-server/commit/693d35d433e3f3d9b42f17ae8271c5c0ca3c9203))

- Add python-semantic-release configuration in pyproject.toml - Create automated release workflow
  for GitHub Actions - Update existing deploy workflow to focus on testing only - Add initial
  CHANGELOG.md with project features - Configure conventional commits for version management -
  Support production releases on main branch - Support prerelease versions on dev branches - Include
  comprehensive documentation in CLAUDE.md

- Simplify template visibility policy
  ([`b0632b2`](https://github.com/mrgoonie/devpocket-server/commit/b0632b2ec8128a4b5d01622b7aa7ba08bafdb30e))

- All users can now see active and beta templates (no subscription restrictions) - Only admin users
  (pro/admin plans) can see deprecated templates - Updated API documentation and comments to reflect
  new access policy - Improved user experience by removing artificial template restrictions -
  Maintains admin-only access to deprecated templates for management purposes

- Enhance API with trailing slash handling and comprehensive error docs
  ([`40e4f97`](https://github.com/mrgoonie/devpocket-server/commit/40e4f97df349d9ba20c284ead64ce2e3f3f0ff05))

- Add TrailingSlashRedirectMiddleware for consistent URL handling across all endpoints - Create
  comprehensive error response schemas for OpenAPI documentation - Update auth and environment
  endpoints with detailed error documentation - Remove email verification requirement for
  environment creation endpoint - Add middleware to automatically redirect trailing slash URLs to
  canonical form - Improve developer experience with better API documentation

- Integrate Resend API for email sending
  ([`974a4c3`](https://github.com/mrgoonie/devpocket-server/commit/974a4c33fb193612b27962f2eb8e42dbc9adee2b))

- Add resend package to requirements.txt - Create email service with verification, welcome, and
  password reset templates - Update auth endpoints to send emails for registration and verification
  - Configure RESEND_API_KEY and EMAIL_FROM in settings - Use noreply@devpocket.sh as sender address

- Add template seeding scripts with ENV_FILE support
  ([`7539f7d`](https://github.com/mrgoonie/devpocket-server/commit/7539f7d35492c18da47d8708923bb038187b1e99))

- Add scripts/seed_templates.py for seeding default environment templates - Add
  scripts/show_default_templates.py to display available templates - Both scripts support ENV_FILE
  environment variable for different configs - Fix template_service.get_default_templates() to
  return dicts instead of TemplateInDB - Update CLAUDE.md with seeding documentation and usage
  examples - Templates include Python, Node.js, Go, Rust, and Ubuntu environments

- Mount /home directory instead of /workspace for better user experience
  ([`8e32c61`](https://github.com/mrgoonie/devpocket-server/commit/8e32c61a9f4343e629869d5afc0aa58e1fce007a))

- Change PVC mount from /workspace to /home directory - Create devuser with home directory setup
  during container init - Create /home/devuser/workspace directory for user projects - Add symlink
  /workspace -> /home/devuser/workspace for compatibility - Set working directory to
  /home/devuser/workspace - Enable persistence of user config files (.bashrc, SSH keys, etc.) - All
  user data now persists in home directory (10Gi volume) - System packages still persist in separate
  5Gi volume

- Implement real Kubernetes deployments with persistent storage
  ([`840362e`](https://github.com/mrgoonie/devpocket-server/commit/840362e1b3e18eaeb1ab8e2c240065c5d9d2dc08))

- Replace simulated container creation with actual Kubernetes deployments - Add persistent volume
  claims for workspace and system directories - Mount /var/lib/apt, /usr/local, /opt for package
  persistence - Use microk8s-hostpath storage class for PVCs - Add SSL bypass for testing with
  self-signed certificates - Create comprehensive test scripts for environment verification - Ensure
  installed packages persist across pod restarts

- Implement real Kubernetes deployment for environments
  ([`2d12025`](https://github.com/mrgoonie/devpocket-server/commit/2d1202551a3b19d6d8622557721a4823de475142))

- Replace simulated container creation with actual Kubernetes deployments - Add support for
  PersistentVolumeClaims, Services, and Deployments - Integrate with cluster service for kubeconfig
  management - Use code-server image for web-based development environments - Configure proper
  resource limits and security contexts - Fix ObjectId handling in cluster service kubeconfig
  decryption - Add SSL verification bypass for testing with self-signed certificates - Environment
  creation now results in real running containers in K8s cluster

- Implement missing auth endpoints /refresh and /verify-email
  ([`7979a4e`](https://github.com/mrgoonie/devpocket-server/commit/7979a4e6d9931c2f91fa47987a74d9f485e27bec))

- Add /api/v1/auth/refresh endpoint for token refresh functionality - Enhance
  /api/v1/auth/verify-email endpoint with proper token validation - Add
  /api/v1/auth/resend-verification endpoint for convenience - Add RefreshTokenRequest and
  EmailVerificationRequest models - Add email verification token fields to UserInDB model -
  Implement refresh_tokens, generate_email_verification_token, and verify_email_token methods in
  AuthService - Add missing get_user_by_id method in AuthService - Update user registration to
  automatically generate verification tokens - Add proper error handling and audit logging

- Add comprehensive testing infrastructure and CI integration
  ([`82d9cb0`](https://github.com/mrgoonie/devpocket-server/commit/82d9cb002f229c648c0be09bebf19bd61d6b341d))

- Add comprehensive test coverage for template endpoints (15 tests) - Add extensive tests for
  environment restart/logs endpoints (11 tests) - Create GitHub Actions CI/CD workflow with
  MongoDB/Redis services - Include security scanning with Trivy and Docker build testing - Add
  integration tests and template initialization verification - Fix pytest async configuration for
  proper test execution - Update test fixtures for better async/await support

- Enhance API documentation with comprehensive OpenAPI/Swagger specs
  ([`3a7719c`](https://github.com/mrgoonie/devpocket-server/commit/3a7719c5e64180345d2f292ef0f14ab75a13a4f3))

- Add detailed OpenAPI documentation for all template endpoints: * Rich response examples with real
  template data * Query parameter documentation with examples * Comprehensive error response
  documentation * Admin-only endpoint annotations

- Enhance environment endpoints documentation: * POST /environments/{id}/restart with process steps
  * GET /environments/{id}/logs with query params and examples * Detailed response schemas with
  sample data

- Improve request/response models: * Add json_schema_extra with realistic examples * Java template
  example for POST requests * Update examples for PATCH operations

- Documentation features: * Interactive 'Try it out' in Swagger UI * Categorized endpoints with tags
  * Path parameter descriptions and examples * Rich markdown descriptions with feature lists

- Fix Pydantic v2 compatibility (schema_extra → json_schema_extra)

- Add missing API endpoints for templates, environment restart and logs
  ([`257b97d`](https://github.com/mrgoonie/devpocket-server/commit/257b97df3eeb5f758c42659ccb93db87cae7ab29))

- Add comprehensive template management system: * Template models with Python, Node.js, Go, Rust,
  Ubuntu defaults * Template service with CRUD operations and default initialization * GET
  /api/v1/templates - List all templates with filtering * GET /api/v1/templates/{id} - Get specific
  template * POST /api/v1/templates - Create template (Admin only) * PUT /api/v1/templates/{id} -
  Update template (Admin only) * DELETE /api/v1/templates/{id} - Delete template (Admin only)

- Add environment restart functionality: * POST /api/v1/environments/{id}/restart - Restart
  environment * Proper status management and async container restart simulation

- Add environment logs retrieval: * GET /api/v1/environments/{id}/logs - Get environment logs *
  Support for line limits and timestamp filtering * Template-specific simulated logs with realistic
  content

- Update database indexes for templates and metrics - Add proper error handling and audit logging -
  Include admin-only permissions for template management

- Add southeast-asia region and OVH cluster integration
  ([`fbe1760`](https://github.com/mrgoonie/devpocket-server/commit/fbe176092f140d9d25286dd60cbb40aa5675791f))

- Add SOUTHEAST_ASIA region to ClusterRegion enum - Fix ObjectId string conversion issues in cluster
  service - Create automated script to add default OVH Kubernetes cluster - Configure cluster with
  southeast-asia region as default - Support for both interactive and non-interactive script
  execution

- Add comprehensive testing infrastructure and CI integration
  ([`0bd920c`](https://github.com/mrgoonie/devpocket-server/commit/0bd920c17140359b47611131d3738cfaad00c949))

- Create complete test suite covering all API endpoints (auth, environments, health, websocket) -
  Add ObjectId validation fix verification tests - Implement Docker-based test runner with isolated
  test environment - Create test-specific Docker Compose configuration with MongoDB and Redis - Add
  comprehensive test fixtures and configuration (pytest.ini) - Integrate tests into GitHub Actions
  CI/CD pipeline - Add code coverage reporting and quality checks - Include both local and
  containerized test execution options - Add test dependencies and requirements management

- Add comprehensive Kubernetes deployment and CI/CD pipeline
  ([`5970e89`](https://github.com/mrgoonie/devpocket-server/commit/5970e899e49c215ff88affb7c9eacc7ffe59ff14))

- Create complete Kubernetes manifests (namespace, deployment, service, ingress, HPA) - Add GitHub
  Actions workflow for automated build and deploy on main branch - Implement semantic versioning
  with Git tags - Add deployment and secret management scripts - Configure multi-platform Docker
  builds for production - Add horizontal pod autoscaling (3-10 replicas) - Include health checks,
  security contexts, and resource limits - Add comprehensive deployment documentation - Support both
  automated and manual deployment workflows

- Add multi-cluster support and test user creation script
  ([`f999735`](https://github.com/mrgoonie/devpocket-server/commit/f9997355fe996217d7651257529ae1dc46c0daba))

- Initialize FastAPI server with auth, environments and websocket endpoints
  ([`3b2c8a9`](https://github.com/mrgoonie/devpocket-server/commit/3b2c8a95e15beec72af539d1db926fd8db4db997))
