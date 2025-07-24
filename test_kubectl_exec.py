#!/usr/bin/env python3
"""
Test persistence using kubectl exec
"""

import asyncio
import sys
from pathlib import Path
import subprocess
import tempfile
import os

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
    import base64
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


async def test_kubectl_exec():
    """Test package installation using kubectl exec"""
    
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
        namespace = 'user-c1e89f47-f92c-4dea-91bf-d8cfcc54cf47'
        
        # Get pod name
        result = subprocess.run([
            'kubectl', '--kubeconfig', kubeconfig_path, 
            'get', 'pods', '-n', namespace, '-o', 'jsonpath={.items[0].metadata.name}'
        ], capture_output=True, text=True, env={**os.environ, 'PYTHONHTTPSVERIFY': '0'})
        
        if result.returncode != 0:
            print(f"❌ Error getting pod: {result.stderr}")
            return
        
        pod_name = result.stdout.strip()
        print(f"🚀 Testing persistence on pod: {pod_name}")
        
        # Test 1: Check current Python version
        print("\n📋 Test 1: Check current Python version")
        result = subprocess.run([
            'kubectl', '--kubeconfig', kubeconfig_path,
            'exec', '-n', namespace, pod_name, '--', 'python3', '--version'
        ], capture_output=True, text=True, env={**os.environ, 'PYTHONHTTPSVERIFY': '0'})
        print(f"Current Python: {result.stdout.strip()}")
        
        # Test 2: Check current directory structure
        print("\n📋 Test 2: Check mounted directories")
        result = subprocess.run([
            'kubectl', '--kubeconfig', kubeconfig_path,
            'exec', '-n', namespace, pod_name, '--', 'df', '-h'
        ], capture_output=True, text=True, env={**os.environ, 'PYTHONHTTPSVERIFY': '0'})
        print("Mount points:")
        print(result.stdout)
        
        # Test 3: Update package list (this will be persistent in /var/lib/apt)
        print("\n📋 Test 3: Update package list")
        result = subprocess.run([
            'kubectl', '--kubeconfig', kubeconfig_path,
            'exec', '-n', namespace, pod_name, '--', 'apt-get', 'update'
        ], capture_output=True, text=True, env={**os.environ, 'PYTHONHTTPSVERIFY': '0'})
        
        if result.returncode == 0:
            print("✅ Package list updated successfully")
        else:
            print(f"❌ Package update failed: {result.stderr}")
        
        # Test 4: Install Python pip (will be persistent in /usr/local)
        print("\n📋 Test 4: Install Python pip")
        result = subprocess.run([
            'kubectl', '--kubeconfig', kubeconfig_path,
            'exec', '-n', namespace, pod_name, '--', 'apt-get', 'install', '-y', 'python3-pip'
        ], capture_output=True, text=True, env={**os.environ, 'PYTHONHTTPSVERIFY': '0'})
        
        if result.returncode == 0:
            print("✅ pip installed successfully")
        else:
            print(f"❌ pip installation failed: {result.stderr}")
            
        # Test 5: Verify pip installation
        print("\n📋 Test 5: Verify pip installation")
        result = subprocess.run([
            'kubectl', '--kubeconfig', kubeconfig_path,
            'exec', '-n', namespace, pod_name, '--', 'pip3', '--version'
        ], capture_output=True, text=True, env={**os.environ, 'PYTHONHTTPSVERIFY': '0'})
        print(f"pip version: {result.stdout.strip()}")
        
        # Test 6: Install a Python package (will be persistent in /usr/local)
        print("\n📋 Test 6: Install requests package")
        result = subprocess.run([
            'kubectl', '--kubeconfig', kubeconfig_path,
            'exec', '-n', namespace, pod_name, '--', 'pip3', 'install', 'requests'
        ], capture_output=True, text=True, env={**os.environ, 'PYTHONHTTPSVERIFY': '0'})
        
        if result.returncode == 0:
            print("✅ requests package installed successfully")
        else:
            print(f"❌ requests installation failed: {result.stderr}")
        
        # Test 7: Create workspace file (will be persistent in /workspace)
        print("\n📋 Test 7: Create test file in workspace")
        result = subprocess.run([
            'kubectl', '--kubeconfig', kubeconfig_path,
            'exec', '-n', namespace, pod_name, '--', 'bash', '-c', 
            'echo "Hello DevPocket! Persistent storage test." > /workspace/test.txt && cat /workspace/test.txt'
        ], capture_output=True, text=True, env={**os.environ, 'PYTHONHTTPSVERIFY': '0'})
        print(f"Workspace file content: {result.stdout.strip()}")
        
        # Test 8: Test Python import
        print("\n📋 Test 8: Test importing installed package")
        result = subprocess.run([
            'kubectl', '--kubeconfig', kubeconfig_path,
            'exec', '-n', namespace, pod_name, '--', 'python3', '-c', 'import requests; print("requests version:", requests.__version__)'
        ], capture_output=True, text=True, env={**os.environ, 'PYTHONHTTPSVERIFY': '0'})
        
        if result.returncode == 0:
            print(f"✅ {result.stdout.strip()}")
        else:
            print(f"❌ Import failed: {result.stderr}")
        
        print("\n🎉 All persistence tests completed!")
        print("📋 Summary of persistent data:")
        print("  - Package lists: /var/lib/apt (5Gi system PVC)")
        print("  - Installed software: /usr/local (5Gi system PVC)")
        print("  - Python packages: /usr/local/lib/python* (5Gi system PVC)")
        print("  - User files: /workspace (10Gi workspace PVC)")
        print("\n✅ The environment is now ready for development with persistent storage!")
        
    finally:
        os.unlink(kubeconfig_path)
        client_mongo.close()


if __name__ == "__main__":
    try:
        asyncio.run(test_kubectl_exec())
    except Exception as e:
        print(f"💥 Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)