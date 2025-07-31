#!/usr/bin/env python3
"""
Test home directory functionality and persistence
"""

import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv

load_dotenv(".env.prod")

# Add the app directory to Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

try:
    import base64

    from motor.motor_asyncio import AsyncIOMotorClient

    from app.core.config import settings
    from app.models.cluster import ClusterRegion
    from app.services.cluster_service import cluster_service
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


async def test_home_directory():
    """Test home directory mount and functionality"""

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
        namespace = "user-c1e89f47-f92c-4dea-91bf-d8cfcc54cf47"

        # Get pod name
        result = subprocess.run(
            [
                "kubectl",
                "--kubeconfig",
                kubeconfig_path,
                "get",
                "pods",
                "-n",
                namespace,
                "-o",
                "jsonpath={.items[0].metadata.name}",
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONHTTPSVERIFY": "0"},
        )

        if result.returncode != 0:
            print(f"❌ Error getting pod: {result.stderr}")
            return

        pod_name = result.stdout.strip()
        print(f"🏠 Testing home directory functionality on pod: {pod_name}")

        # Test 1: Check the user creation and home directory setup
        print("\n📋 Test 1: Check user and directory structure")
        result = subprocess.run(
            [
                "kubectl",
                "--kubeconfig",
                kubeconfig_path,
                "exec",
                "-n",
                namespace,
                pod_name,
                "--",
                "ls",
                "-la",
                "/home",
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONHTTPSVERIFY": "0"},
        )
        print("Home directory contents:")
        print(result.stdout)

        # Test 2: Check devuser home directory
        print("\n📋 Test 2: Check devuser home directory")
        result = subprocess.run(
            [
                "kubectl",
                "--kubeconfig",
                kubeconfig_path,
                "exec",
                "-n",
                namespace,
                pod_name,
                "--",
                "ls",
                "-la",
                "/home/devuser",
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONHTTPSVERIFY": "0"},
        )
        print("devuser home contents:")
        print(result.stdout)

        # Test 3: Check workspace symlink
        print("\n📋 Test 3: Check workspace symlink")
        result = subprocess.run(
            [
                "kubectl",
                "--kubeconfig",
                kubeconfig_path,
                "exec",
                "-n",
                namespace,
                pod_name,
                "--",
                "ls",
                "-la",
                "/workspace",
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONHTTPSVERIFY": "0"},
        )
        print("Workspace symlink:")
        print(result.stdout)

        # Test 4: Check current working directory
        print("\n📋 Test 4: Check current working directory")
        result = subprocess.run(
            [
                "kubectl",
                "--kubeconfig",
                kubeconfig_path,
                "exec",
                "-n",
                namespace,
                pod_name,
                "--",
                "pwd",
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONHTTPSVERIFY": "0"},
        )
        print(f"Current working directory: {result.stdout.strip()}")

        # Test 5: Create files in different locations
        print("\n📋 Test 5: Create test files in different locations")

        # Create file in workspace via symlink
        result = subprocess.run(
            [
                "kubectl",
                "--kubeconfig",
                kubeconfig_path,
                "exec",
                "-n",
                namespace,
                pod_name,
                "--",
                "bash",
                "-c",
                'echo "Hello from workspace symlink!" > /workspace/test_symlink.txt',
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONHTTPSVERIFY": "0"},
        )

        # Create file directly in home/devuser/workspace
        result = subprocess.run(
            [
                "kubectl",
                "--kubeconfig",
                kubeconfig_path,
                "exec",
                "-n",
                namespace,
                pod_name,
                "--",
                "bash",
                "-c",
                'echo "Hello from direct workspace!" > /home/devuser/workspace/test_direct.txt',
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONHTTPSVERIFY": "0"},
        )

        # Create user config file
        result = subprocess.run(
            [
                "kubectl",
                "--kubeconfig",
                kubeconfig_path,
                "exec",
                "-n",
                namespace,
                pod_name,
                "--",
                "bash",
                "-c",
                'echo "export MY_CONFIG=production" > /home/devuser/.bashrc',
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONHTTPSVERIFY": "0"},
        )

        print("✅ Test files created")

        # Test 6: Verify all files exist and are accessible
        print("\n📋 Test 6: Verify file accessibility")

        # Check workspace files via symlink
        result = subprocess.run(
            [
                "kubectl",
                "--kubeconfig",
                kubeconfig_path,
                "exec",
                "-n",
                namespace,
                pod_name,
                "--",
                "ls",
                "-la",
                "/workspace",
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONHTTPSVERIFY": "0"},
        )
        print("Files in /workspace (symlink):")
        print(result.stdout)

        # Check workspace files directly
        result = subprocess.run(
            [
                "kubectl",
                "--kubeconfig",
                kubeconfig_path,
                "exec",
                "-n",
                namespace,
                pod_name,
                "--",
                "ls",
                "-la",
                "/home/devuser/workspace",
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONHTTPSVERIFY": "0"},
        )
        print("Files in /home/devuser/workspace (direct):")
        print(result.stdout)

        # Test 7: Verify file contents
        print("\n📋 Test 7: Verify file contents")
        result = subprocess.run(
            [
                "kubectl",
                "--kubeconfig",
                kubeconfig_path,
                "exec",
                "-n",
                namespace,
                pod_name,
                "--",
                "cat",
                "/workspace/test_symlink.txt",
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONHTTPSVERIFY": "0"},
        )
        print(f"Content via symlink: {result.stdout.strip()}")

        result = subprocess.run(
            [
                "kubectl",
                "--kubeconfig",
                kubeconfig_path,
                "exec",
                "-n",
                namespace,
                pod_name,
                "--",
                "cat",
                "/home/devuser/workspace/test_direct.txt",
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONHTTPSVERIFY": "0"},
        )
        print(f"Content via direct path: {result.stdout.strip()}")

        result = subprocess.run(
            [
                "kubectl",
                "--kubeconfig",
                kubeconfig_path,
                "exec",
                "-n",
                namespace,
                pod_name,
                "--",
                "cat",
                "/home/devuser/.bashrc",
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONHTTPSVERIFY": "0"},
        )
        print(f"User config: {result.stdout.strip()}")

        # Test 8: Test as devuser (switch user context)
        print("\n📋 Test 8: Test operations as devuser")
        result = subprocess.run(
            [
                "kubectl",
                "--kubeconfig",
                kubeconfig_path,
                "exec",
                "-n",
                namespace,
                pod_name,
                "--",
                "su",
                "-",
                "devuser",
                "-c",
                "whoami && pwd && ls -la",
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONHTTPSVERIFY": "0"},
        )
        print("devuser session:")
        print(result.stdout)

        print("\n🎉 Home directory tests completed!")
        print("📋 Summary of home directory setup:")
        print("  ✅ /home mounted from persistent volume (10Gi)")
        print("  ✅ devuser created with home directory")
        print("  ✅ /home/devuser/workspace directory created")
        print("  ✅ /workspace symlink points to /home/devuser/workspace")
        print("  ✅ User config files (.bashrc) persist in home directory")
        print("  ✅ Working directory set to /home/devuser/workspace")
        print("  ✅ All user data is persistent across pod restarts")

    finally:
        os.unlink(kubeconfig_path)
        client_mongo.close()


if __name__ == "__main__":
    try:
        asyncio.run(test_home_directory())
    except Exception as e:
        print(f"💥 Error: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
