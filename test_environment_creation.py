#!/usr/bin/env python3
"""
Test script to create an environment and verify it's deployed to Kubernetes
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

# Load environment variables
from dotenv import load_dotenv

load_dotenv(".env.prod")

try:
    import uuid
    from datetime import datetime

    from motor.motor_asyncio import AsyncIOMotorClient

    from app.core.config import settings
    from app.models.environment import (
        EnvironmentCreate,
        EnvironmentTemplate,
        ResourceLimits,
    )
    from app.models.user import UserInDB
    from app.services.auth_service import auth_service
    from app.services.environment_service import environment_service
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


async def create_test_user():
    """Create a test user for environment creation"""

    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    # Initialize services
    environment_service.set_database(db)
    auth_service.set_database(db)

    # Check if test user exists
    test_email = "test@devpocket.io"
    existing_user = await db.users.find_one({"email": test_email})

    if existing_user:
        print(f"Test user already exists: {test_email}")
        return UserInDB(**existing_user)

    # Create test user
    test_user_data = {
        "_id": str(uuid.uuid4()),
        "username": "testuser",
        "email": test_email,
        "hashed_password": "dummy_hash",
        "subscription_plan": "pro",  # Give pro plan for better resources
        "is_verified": True,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    await db.users.insert_one(test_user_data)
    print(f"✅ Created test user: {test_email}")

    return UserInDB(**test_user_data)


async def test_environment_creation():
    """Test creating an environment"""

    try:
        # Create test user
        user = await create_test_user()
        print(f"Using user: {user.username} ({user.email})")

        # Create environment data
        env_data = EnvironmentCreate(
            name=f"test-env-{uuid.uuid4().hex[:8]}",
            template=EnvironmentTemplate.PYTHON,
            resources=ResourceLimits(cpu="1000m", memory="2Gi", storage="10Gi"),
            environment_variables={"NODE_ENV": "development", "DEBUG": "true"},
        )

        print(f"🚀 Creating environment: {env_data.name}")
        print(f"   Template: {env_data.template.value}")
        print(
            f"   Resources: CPU={env_data.resources.cpu}, Memory={env_data.resources.memory}, Storage={env_data.resources.storage}"
        )

        # Create environment
        environment = await environment_service.create_environment(user, env_data)

        print(f"✅ Environment creation initiated:")
        print(f"   ID: {environment.id}")
        print(f"   Name: {environment.name}")
        print(f"   Status: {environment.status.value}")
        print(f"   Namespace: {environment.namespace}")
        print(f"   Pod Name: {environment.pod_name}")
        print(f"   Service Name: {environment.service_name}")

        # Wait a bit and check status
        print("\n⏳ Waiting for environment to be created...")
        await asyncio.sleep(5)

        # Check updated status
        updated_env = await environment_service.get_environment(
            environment.id, str(user.id)
        )
        if updated_env:
            print(f"📊 Current status: {updated_env.status.value}")
            if hasattr(updated_env, "external_url") and updated_env.external_url:
                print(f"🌐 External URL: {updated_env.external_url}")
            if hasattr(updated_env, "internal_url") and updated_env.internal_url:
                print(f"🔗 Internal URL: {updated_env.internal_url}")

        return environment

    except Exception as e:
        print(f"❌ Error creating environment: {str(e)}")
        import traceback

        traceback.print_exc()
        return None


async def verify_kubernetes_deployment():
    """Verify the deployment exists in Kubernetes"""
    try:
        import base64
        import tempfile

        from kubernetes import client, config as k8s_config

        from app.models.cluster import ClusterRegion
        from app.services.cluster_service import cluster_service

        # Connect to MongoDB
        client_mongo = AsyncIOMotorClient(settings.MONGODB_URL)
        db = client_mongo[settings.DATABASE_NAME]
        cluster_service.set_database(db)

        # Get cluster
        cluster = await cluster_service.get_cluster_by_region(
            ClusterRegion.SOUTHEAST_ASIA
        )
        if not cluster:
            print("❌ No cluster found")
            return False

        # Get kubeconfig
        kubeconfig_content = await cluster_service.get_decrypted_kubeconfig(cluster.id)
        if not kubeconfig_content:
            print("❌ Failed to get kubeconfig")
            return False

        # Load kubeconfig
        kubeconfig_yaml = base64.b64decode(kubeconfig_content).decode("utf-8")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as temp_kubeconfig:
            temp_kubeconfig.write(kubeconfig_yaml)
            kubeconfig_path = temp_kubeconfig.name

        try:
            k8s_config.load_kube_config(config_file=kubeconfig_path)

            # Disable SSL verification for testing
            from kubernetes.client.configuration import Configuration

            config = Configuration.get_default_copy()
            config.verify_ssl = False
            config.ssl_ca_cert = None
            Configuration.set_default(config)

            v1_core = client.CoreV1Api()
            v1_apps = client.AppsV1Api()

            print("\n🔍 Checking Kubernetes resources...")

            # List namespaces
            namespaces = v1_core.list_namespace()
            devpocket_namespaces = [
                ns.metadata.name
                for ns in namespaces.items
                if ns.metadata.name.startswith("user-")
            ]
            print(f"📁 DevPocket namespaces: {devpocket_namespaces}")

            # List deployments in each namespace
            for namespace in devpocket_namespaces:
                try:
                    deployments = v1_apps.list_namespaced_deployment(
                        namespace=namespace
                    )
                    for deployment in deployments.items:
                        print(
                            f"🚀 Deployment: {deployment.metadata.name} in {namespace}"
                        )
                        print(
                            f"   Status: Ready={deployment.status.ready_replicas}/{deployment.status.replicas}"
                        )

                    # List services
                    services = v1_core.list_namespaced_service(namespace=namespace)
                    for service in services.items:
                        if service.metadata.name.startswith("svc-"):
                            print(f"🔗 Service: {service.metadata.name}")
                            print(
                                f"   Ports: {[f'{p.port}:{p.target_port}' for p in service.spec.ports]}"
                            )

                    # List PVCs
                    pvcs = v1_core.list_namespaced_persistent_volume_claim(
                        namespace=namespace
                    )
                    for pvc in pvcs.items:
                        if pvc.metadata.name.startswith("pvc-"):
                            print(f"💾 PVC: {pvc.metadata.name}")
                            print(f"   Status: {pvc.status.phase}")
                            print(
                                f"   Size: {pvc.spec.resources.requests.get('storage', 'unknown')}"
                            )

                except Exception as e:
                    print(f"❌ Error listing resources in {namespace}: {e}")

            return True

        finally:
            os.unlink(kubeconfig_path)

    except Exception as e:
        print(f"❌ Error verifying Kubernetes deployment: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    print("🧪 Testing Environment Creation with Kubernetes Deployment")
    print("=" * 60)

    # Test environment creation
    environment = await test_environment_creation()

    if environment:
        print("\n" + "=" * 60)

        # Wait a bit more for deployment to complete
        print("⏳ Waiting 30 seconds for deployment to complete...")
        await asyncio.sleep(30)

        # Verify Kubernetes deployment
        print("\n🔍 Verifying Kubernetes deployment...")
        await verify_kubernetes_deployment()

        print("\n✅ Test completed!")
    else:
        print("\n❌ Test failed!")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Test cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
