#!/usr/bin/env python3
"""
Cleanup script to remove test environments from both Kubernetes and database
"""

import asyncio
import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv

load_dotenv(".env.prod")

# Add the app directory to Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

try:
    import base64
    import os
    import tempfile

    from kubernetes import client, config as k8s_config
    from kubernetes.client.exceptions import ApiException
    from motor.motor_asyncio import AsyncIOMotorClient

    from app.core.config import settings
    from app.models.cluster import ClusterRegion
    from app.services.cluster_service import cluster_service
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


async def cleanup_kubernetes_resources():
    """Clean up all DevPocket test resources from Kubernetes"""
    print("🧹 Cleaning up Kubernetes resources...")

    try:
        # Connect to MongoDB to get cluster config
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

            # Find DevPocket namespaces
            namespaces = v1_core.list_namespace()
            devpocket_namespaces = [
                ns.metadata.name
                for ns in namespaces.items
                if ns.metadata.name.startswith("user-")
            ]

            print(f"📁 Found DevPocket namespaces: {devpocket_namespaces}")

            for namespace in devpocket_namespaces:
                print(f"\n🗑️  Cleaning up namespace: {namespace}")

                try:
                    # Delete all deployments
                    deployments = v1_apps.list_namespaced_deployment(
                        namespace=namespace
                    )
                    for deployment in deployments.items:
                        print(f"   🚀 Deleting deployment: {deployment.metadata.name}")
                        v1_apps.delete_namespaced_deployment(
                            name=deployment.metadata.name, namespace=namespace
                        )

                    # Delete all services (except default)
                    services = v1_core.list_namespaced_service(namespace=namespace)
                    for service in services.items:
                        if service.metadata.name != "default":
                            print(f"   🔗 Deleting service: {service.metadata.name}")
                            v1_core.delete_namespaced_service(
                                name=service.metadata.name, namespace=namespace
                            )

                    # Delete all PVCs (home, workspace, and system)
                    pvcs = v1_core.list_namespaced_persistent_volume_claim(
                        namespace=namespace
                    )
                    for pvc in pvcs.items:
                        print(f"   💾 Deleting PVC: {pvc.metadata.name}")
                        try:
                            v1_core.delete_namespaced_persistent_volume_claim(
                                name=pvc.metadata.name, namespace=namespace
                            )
                        except ApiException as pvc_e:
                            print(
                                f"   ⚠️  Warning deleting PVC {pvc.metadata.name}: {pvc_e}"
                            )

                    # Wait a bit for resources to be deleted
                    await asyncio.sleep(5)

                    # Delete the namespace itself
                    print(f"   📁 Deleting namespace: {namespace}")
                    v1_core.delete_namespace(name=namespace)

                except ApiException as e:
                    print(f"   ❌ Error cleaning namespace {namespace}: {e}")

        finally:
            os.unlink(kubeconfig_path)
            client_mongo.close()

        print("✅ Kubernetes cleanup completed!")
        return True

    except Exception as e:
        print(f"❌ Error cleaning Kubernetes resources: {e}")
        return False


async def cleanup_database_environments():
    """Clean up test environments from database"""
    print("\n🗄️  Cleaning up database environments...")

    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    try:
        # Delete all test environments for our test user
        result = await db.environments.delete_many(
            {"user_id": "c1e89f47-f92c-4dea-91bf-d8cfcc54cf47"}
        )

        print(f"🗑️  Deleted {result.deleted_count} environment records")

        # Delete WebSocket sessions
        ws_result = await db.websocket_sessions.delete_many(
            {"user_id": "c1e89f47-f92c-4dea-91bf-d8cfcc54cf47"}
        )

        print(f"🔌 Deleted {ws_result.deleted_count} WebSocket session records")

        # Delete environment metrics
        metrics_result = await db.environment_metrics.delete_many({})
        print(f"📊 Deleted {metrics_result.deleted_count} metrics records")

        print("✅ Database cleanup completed!")

    except Exception as e:
        print(f"❌ Error cleaning database: {e}")
    finally:
        client.close()


async def main():
    """Main cleanup function"""
    print("🧪 DevPocket Test Environment Cleanup")
    print("=" * 50)

    # Clean up Kubernetes resources first
    k8s_success = await cleanup_kubernetes_resources()

    # Clean up database
    await cleanup_database_environments()

    if k8s_success:
        print("\n🎉 Cleanup completed successfully!")
        print("Ready for fresh environment testing!")
    else:
        print("\n⚠️  Cleanup completed with some issues")
        print("Database cleaned, but some Kubernetes resources may remain")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Cleanup cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
