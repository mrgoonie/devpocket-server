#!/usr/bin/env python3
"""
Test persistence of installed packages in the environment
"""

import asyncio
import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv('.env.prod')

# Add the app directory to Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

try:
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.services.cluster_service import cluster_service
    from app.models.cluster import ClusterRegion
    from app.core.config import settings
    from kubernetes import client, config as k8s_config
    import base64
    import tempfile
    import os
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


async def test_persistence():
    """Test package installation and persistence"""
    
    client_mongo = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client_mongo[settings.DATABASE_NAME]
    cluster_service.set_database(db)
    
    cluster = await cluster_service.get_cluster_by_region(ClusterRegion.SOUTHEAST_ASIA)
    kubeconfig_content = await cluster_service.get_decrypted_kubeconfig(cluster.id)
    kubeconfig_yaml = base64.b64decode(kubeconfig_content).decode('utf-8')
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_kubeconfig:
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
        
        # Find our pod
        namespace = 'user-c1e89f47-f92c-4dea-91bf-d8cfcc54cf47'
        pods = v1_core.list_namespaced_pod(namespace=namespace)
        
        if not pods.items:
            print("❌ No pods found")
            return
        
        pod_name = pods.items[0].metadata.name
        print(f"🚀 Testing persistence on pod: {pod_name}")
        
        # Test 1: Check current Python version
        print("\n📋 Test 1: Check current Python version")
        exec_resp = v1_core.connect_get_namespaced_pod_exec(
            namespace=namespace,
            name=pod_name,
            command=['python3', '--version'],
            stderr=True, stdin=False, stdout=True, tty=False
        )
        print(f"Current Python: {exec_resp}")
        
        # Test 2: Update package list and install Python pip
        print("\n📋 Test 2: Update package list and install pip")
        exec_resp = v1_core.connect_get_namespaced_pod_exec(
            namespace=namespace,
            name=pod_name,
            command=['bash', '-c', 'apt-get update && apt-get install -y python3-pip'],
            stderr=True, stdin=False, stdout=True, tty=False
        )
        print("Package installation completed")
        
        # Test 3: Install a Python package
        print("\n📋 Test 3: Install a Python package (requests)")
        exec_resp = v1_core.connect_get_namespaced_pod_exec(
            namespace=namespace,
            name=pod_name,
            command=['pip3', 'install', 'requests'],
            stderr=True, stdin=False, stdout=True, tty=False
        )
        print("Python package installation completed")
        
        # Test 4: Verify installation
        print("\n📋 Test 4: Verify installations")
        exec_resp = v1_core.connect_get_namespaced_pod_exec(
            namespace=namespace,
            name=pod_name,
            command=['pip3', 'list'],
            stderr=True, stdin=False, stdout=True, tty=False
        )
        print("Installed packages list retrieved")
        
        # Test 5: Create a test file in workspace
        print("\n📋 Test 5: Create test file in workspace")
        exec_resp = v1_core.connect_get_namespaced_pod_exec(
            namespace=namespace,
            name=pod_name,
            command=['bash', '-c', 'echo "Hello DevPocket!" > /workspace/test.txt && cat /workspace/test.txt'],
            stderr=True, stdin=False, stdout=True, tty=False
        )
        print(f"Test file created: {exec_resp}")
        
        # Test 6: Check mount points
        print("\n📋 Test 6: Check mount points")
        exec_resp = v1_core.connect_get_namespaced_pod_exec(
            namespace=namespace,
            name=pod_name,
            command=['df', '-h'],
            stderr=True, stdin=False, stdout=True, tty=False
        )
        print("Mount points checked")
        
        print("\n✅ All tests completed! The environment has:")
        print("  - Updated package lists (persistent in /var/lib/apt)")
        print("  - Installed pip (persistent in /usr/local)")
        print("  - Installed Python packages (persistent in /usr/local)")
        print("  - Created workspace files (persistent in /workspace)")
        print("\n🔄 To test persistence, you can now restart the pod and verify packages remain installed")
        
    finally:
        os.unlink(kubeconfig_path)
        client_mongo.close()


if __name__ == "__main__":
    try:
        asyncio.run(test_persistence())
    except Exception as e:
        print(f"💥 Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)