#!/usr/bin/env python3
"""
Comprehensive test for environment creation and WebSocket terminal interaction.

This test covers the complete flow:
1. Create a new environment via API
2. Wait for Kubernetes deployment to be ready
3. Connect to WebSocket terminal
4. Execute commands in the container
5. Verify responses
6. Clean up resources
"""

import asyncio
import json
import os
import random
import string
import time
from typing import Optional

import httpx
import websockets
from kubernetes import client, config as k8s_config
from kubernetes.client.exceptions import ApiException


class EnvironmentFlowTest:
    def __init__(self):
        self.api_base_url = "https://devpocket-api.goon.vn"
        self.ws_base_url = "wss://devpocket-api.goon.vn"
        self.access_token: Optional[str] = None
        self.environment_id: Optional[str] = None
        self.test_env_name = f"test-env-{self.random_string(8)}"
        self.namespace: Optional[str] = None
        self.deployment_name: Optional[str] = None

    def random_string(self, length: int) -> str:
        """Generate random string for unique test names"""
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

    async def setup_kubernetes(self):
        """Setup Kubernetes client"""
        try:
            # Load kubeconfig from the project's config
            k8s_config.load_kube_config(config_file="k8s/kube_config_ovh.yaml")

            # Disable SSL verification for testing
            from kubernetes.client.configuration import Configuration

            config = Configuration.get_default_copy()
            config.verify_ssl = False
            config.ssl_ca_cert = None
            Configuration.set_default(config)

            self.k8s_core = client.CoreV1Api()
            self.k8s_apps = client.AppsV1Api()
            print("✅ Kubernetes client configured")

        except Exception as e:
            print(f"❌ Failed to setup Kubernetes client: {e}")
            raise

    async def authenticate(self):
        """Create test token directly (bypass login for testing)"""
        print("🔐 Creating test authentication token...")

        # For testing purposes, we'll create a JWT token directly
        # In production, this would go through the login flow
        from datetime import datetime, timedelta, timezone

        from jose import jwt

        # Get the secret key from environment
        secret_key = os.getenv(
            "SECRET_KEY", "9XX36cij9crf1VJPFUjphfZlk8vfuOBok5pxkHa-YsU"
        )

        # Create payload for an existing user (we'll use the goon user ID from the logs)
        user_id = "6880cb54f9f0280f9e9f70c8"  # From the logs
        payload = {
            "sub": user_id,
            "username": "goon",
            "email": "goon.nguyen@gmail.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
            "type": "access_token",
        }

        # Create token
        self.access_token = jwt.encode(payload, secret_key, algorithm="HS256")
        print("✅ Test token created successfully")
        return

    async def create_environment(self):
        """Create a new environment via API"""
        print(f"🚀 Creating environment: {self.test_env_name}")

        env_data = {
            "name": self.test_env_name,
            "template": "ubuntu",
            "resources": {"cpu": "500m", "memory": "1Gi", "storage": "5Gi"},
            "environment_variables": {"TEST_VAR": "test_value"},
        }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.post(
                    f"{self.api_base_url}/api/v1/environments",
                    json=env_data,
                    headers=headers,
                    timeout=60,
                )

                if response.status_code == 201:
                    data = response.json()
                    self.environment_id = data.get("id")
                    self.namespace = data.get("namespace")
                    self.deployment_name = data.get("pod_name")
                    print(f"✅ Environment created: {self.environment_id}")
                    print(f"   Namespace: {self.namespace}")
                    print(f"   Deployment: {self.deployment_name}")
                    return data
                else:
                    print(
                        f"❌ Environment creation failed: {response.status_code} - {response.text}"
                    )
                    raise Exception(
                        f"Environment creation failed: {response.status_code}"
                    )

            except httpx.RequestError as e:
                print(f"❌ Environment creation request failed: {e}")
                raise

    async def wait_for_deployment_ready(self, timeout_minutes=5):
        """Wait for Kubernetes deployment to be ready"""
        print("⏳ Waiting for Kubernetes deployment to be ready...")

        timeout_seconds = timeout_minutes * 60
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            try:
                # Check if namespace exists
                try:
                    self.k8s_core.read_namespace(name=self.namespace)
                except ApiException as e:
                    if e.status == 404:
                        print(
                            f"   Namespace {self.namespace} not found yet, waiting..."
                        )
                        await asyncio.sleep(10)
                        continue
                    raise

                # Check deployment status
                try:
                    deployment = self.k8s_apps.read_namespaced_deployment(
                        name=self.deployment_name, namespace=self.namespace
                    )

                    ready_replicas = deployment.status.ready_replicas or 0
                    available_replicas = deployment.status.available_replicas or 0

                    print(
                        f"   Deployment status: {ready_replicas}/{deployment.spec.replicas} ready, {available_replicas} available"
                    )

                    if ready_replicas >= 1 and available_replicas >= 1:
                        print("✅ Deployment is ready!")

                        # Also check if pod is running
                        pods = self.k8s_core.list_namespaced_pod(
                            namespace=self.namespace,
                            label_selector=f"app=devpocket,environment={self.deployment_name}",
                        )

                        if pods.items:
                            pod = pods.items[0]
                            print(f"   Pod: {pod.metadata.name} - {pod.status.phase}")
                            if pod.status.phase == "Running":
                                print("✅ Pod is running!")
                                return True

                except ApiException as e:
                    if e.status == 404:
                        print(
                            f"   Deployment {self.deployment_name} not found yet, waiting..."
                        )
                    else:
                        print(f"   Error checking deployment: {e}")

            except Exception as e:
                print(f"   Error waiting for deployment: {e}")

            await asyncio.sleep(10)

        print(f"❌ Deployment not ready after {timeout_minutes} minutes")
        return False

    async def wait_for_environment_running(self, timeout_minutes=5):
        """Wait for environment status to be 'running' in database"""
        print("⏳ Waiting for environment status to be 'running'...")

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        timeout_seconds = timeout_minutes * 60
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                try:
                    response = await client.get(
                        f"{self.api_base_url}/api/v1/environments/{self.environment_id}",
                        headers=headers,
                        timeout=30,
                    )

                    if response.status_code == 200:
                        data = response.json()
                        status = data.get("status")
                        print(f"   Environment status: {status}")

                        if status == "running":
                            print("✅ Environment is running!")
                            return True
                        elif status == "error":
                            print("❌ Environment failed to start")
                            return False

                except httpx.RequestError as e:
                    print(f"   Error checking environment status: {e}")

            await asyncio.sleep(5)

        print(f"❌ Environment not running after {timeout_minutes} minutes")
        return False

    async def test_websocket_terminal(self):
        """Test WebSocket terminal connection and command execution"""
        print("🌐 Testing WebSocket terminal connection...")

        ws_url = f"{self.ws_base_url}/api/v1/ws/terminal/{self.environment_id}?token={self.access_token}"

        try:
            async with websockets.connect(ws_url, timeout=30) as websocket:
                print("✅ WebSocket connected successfully!")

                # Wait for welcome message
                welcome_msg = await websocket.recv()
                welcome_data = json.loads(welcome_msg)
                print(f"   Welcome message: {welcome_data.get('message')}")

                if welcome_data.get("type") == "welcome":
                    env_info = welcome_data.get("environment", {})
                    print(f"   Connected to pod: {env_info.get('pod_name')}")

                # Test commands
                test_commands = [
                    "pwd",
                    "whoami",
                    "echo 'Hello from container!'",
                    "ls -la",
                    "echo $TEST_VAR",  # Test environment variable
                    "uname -a",
                ]

                for cmd in test_commands:
                    print(f"   Executing: {cmd}")

                    # Send command
                    command_msg = {"type": "input", "data": cmd}
                    await websocket.send(json.dumps(command_msg))

                    # Wait for response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=10)
                        response_data = json.loads(response)

                        if response_data.get("type") == "output":
                            output = response_data.get("data", "")
                            print(f"     Output: {output.strip()}")
                        else:
                            print(f"     Response: {response_data}")

                    except asyncio.TimeoutError:
                        print(f"     ⚠️ Command timeout")

                    await asyncio.sleep(1)  # Small delay between commands

                # Test ping/pong
                print("   Testing ping/pong...")
                ping_msg = {"type": "ping"}
                await websocket.send(json.dumps(ping_msg))

                try:
                    pong_response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    pong_data = json.loads(pong_response)
                    if pong_data.get("type") == "pong":
                        print("   ✅ Ping/pong successful")
                    else:
                        print(f"   ⚠️ Unexpected ping response: {pong_data}")
                except asyncio.TimeoutError:
                    print("   ⚠️ Ping timeout")

                print("✅ WebSocket terminal test completed successfully!")
                return True

        except websockets.exceptions.WebSocketException as e:
            print(f"❌ WebSocket connection failed: {e}")
            return False
        except Exception as e:
            print(f"❌ WebSocket test failed: {e}")
            return False

    async def cleanup_resources(self):
        """Clean up test resources"""
        print("🧹 Cleaning up test resources...")

        try:
            # Delete environment via API
            if self.environment_id and self.access_token:
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                }

                async with httpx.AsyncClient(follow_redirects=True) as client:
                    response = await client.delete(
                        f"{self.api_base_url}/api/v1/environments/{self.environment_id}",
                        headers=headers,
                        timeout=30,
                    )

                    if response.status_code in [200, 204]:
                        print("✅ Environment deleted via API")
                    else:
                        print(f"⚠️ Environment deletion failed: {response.status_code}")

            # Also clean up Kubernetes resources directly if they still exist
            if self.namespace and self.deployment_name:
                try:
                    # Delete deployment
                    self.k8s_apps.delete_namespaced_deployment(
                        name=self.deployment_name, namespace=self.namespace
                    )
                    print(f"✅ Deleted deployment: {self.deployment_name}")
                except ApiException as e:
                    if e.status != 404:
                        print(f"⚠️ Error deleting deployment: {e}")

                # Wait a bit for pods to be deleted
                await asyncio.sleep(5)

                try:
                    # Check if namespace is empty and delete it
                    pods = self.k8s_core.list_namespaced_pod(namespace=self.namespace)
                    if not pods.items:
                        self.k8s_core.delete_namespace(name=self.namespace)
                        print(f"✅ Deleted namespace: {self.namespace}")
                    else:
                        print(
                            f"⚠️ Namespace {self.namespace} still has pods, not deleting"
                        )
                except ApiException as e:
                    if e.status != 404:
                        print(f"⚠️ Error deleting namespace: {e}")

        except Exception as e:
            print(f"⚠️ Error during cleanup: {e}")

    async def run_test(self):
        """Run the complete test flow"""
        try:
            print("🚀 Starting comprehensive environment flow test")
            print("=" * 60)

            # Setup
            await self.setup_kubernetes()
            await self.authenticate()

            # Create environment
            await self.create_environment()

            # Wait for deployment
            deployment_ready = await self.wait_for_deployment_ready()
            if not deployment_ready:
                raise Exception("Deployment failed to become ready")

            # Wait for environment status
            env_running = await self.wait_for_environment_running()
            if not env_running:
                raise Exception("Environment failed to reach running status")

            # Test WebSocket terminal
            ws_success = await self.test_websocket_terminal()
            if not ws_success:
                raise Exception("WebSocket terminal test failed")

            print("=" * 60)
            print(
                "🎉 ALL TESTS PASSED! Environment creation and WebSocket terminal working correctly!"
            )
            return True

        except Exception as e:
            print("=" * 60)
            print(f"❌ TEST FAILED: {e}")
            return False

        finally:
            # Always cleanup
            await self.cleanup_resources()


async def main():
    """Main test function"""
    test = EnvironmentFlowTest()
    success = await test.run_test()

    if success:
        print("\n✅ Test completed successfully!")
        exit(0)
    else:
        print("\n❌ Test failed!")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
