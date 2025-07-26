#!/usr/bin/env python3
"""
Check persistent volumes and mounts for test environment
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
    from motor.motor_asyncio import AsyncIOMotorClient

    from app.core.config import settings
    from app.models.cluster import ClusterRegion
    from app.services.cluster_service import cluster_service
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


async def check_volumes():
    """Check persistent volumes and mounts"""

    client_mongo = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client_mongo[settings.DATABASE_NAME]
    cluster_service.set_database(db)

    cluster = await cluster_service.get_cluster_by_region(ClusterRegion.SOUTHEAST_ASIA)
    kubeconfig_content = await cluster_service.get_decrypted_kubeconfig(cluster.id)
    kubeconfig_yaml = base64.b64decode(kubeconfig_content).decode("utf-8")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as temp_kubeconfig:
        temp_kubeconfig.write(kubeconfig_yaml)
        kubeconfig_path = temp_kubeconfig.name

    try:
        k8s_config.load_kube_config(config_file=kubeconfig_path)
        from kubernetes.client.configuration import Configuration

        config = Configuration.get_default_copy()
        config.verify_ssl = False
        config.ssl_ca_cert = None
        Configuration.set_default(config)

        v1_core = client.CoreV1Api()

        # Check PVCs
        namespace = "user-c1e89f47-f92c-4dea-91bf-d8cfcc54cf47"
        pvcs = v1_core.list_namespaced_persistent_volume_claim(namespace=namespace)

        print("💾 Persistent Volume Claims:")
        for pvc in pvcs.items:
            print(
                f'  - {pvc.metadata.name}: {pvc.status.phase} ({pvc.spec.resources.requests["storage"]})'
            )

        # Check pod details
        pods = v1_core.list_namespaced_pod(namespace=namespace)
        for pod in pods.items:
            print(f"\n🚀 Pod: {pod.metadata.name}")
            print(f"  Status: {pod.status.phase}")

            print("  Volumes:")
            for volume in pod.spec.volumes:
                if volume.persistent_volume_claim:
                    print(
                        f"    - {volume.name} -> PVC: {volume.persistent_volume_claim.claim_name}"
                    )

            for container in pod.spec.containers:
                print(f"  Container: {container.name}")
                print("    Volume Mounts:")
                for mount in container.volume_mounts:
                    mount_info = f"      {mount.mount_path} <- {mount.name}"
                    if hasattr(mount, "sub_path") and mount.sub_path:
                        mount_info += f" (subPath: {mount.sub_path})"
                    print(mount_info)

    finally:
        os.unlink(kubeconfig_path)
        client_mongo.close()


if __name__ == "__main__":
    try:
        asyncio.run(check_volumes())
    except Exception as e:
        print(f"💥 Error: {str(e)}")
        sys.exit(1)
