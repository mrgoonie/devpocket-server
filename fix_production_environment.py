#!/usr/bin/env python3
"""
Fix production environment data - update namespace and pod_name fields.
"""

import asyncio
import os
import subprocess
from datetime import datetime, timedelta, timezone

import httpx
from jose import jwt


async def fix_production_environment():
    """Fix production environment data via API"""

    # Create JWT token
    secret_key = os.getenv("SECRET_KEY", "9XX36cij9crf1VJPFUjphfZlk8vfuOBok5pxkHa-YsU")
    payload = {
        "sub": "6880cb54f9f0280f9e9f70c8",
        "username": "goon",
        "email": "goon.nguyen@gmail.com",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
        "type": "access_token",
    }
    access_token = jwt.encode(payload, secret_key, algorithm="HS256")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Get the actual pod name from Kubernetes
    print("🔍 Getting actual pod name from Kubernetes...")
    try:
        result = subprocess.run(
            [
                "kubectl",
                "--kubeconfig=k8s/kube_config_ovh.yaml",
                "get",
                "pods",
                "-n",
                "user-6880cb54f9f0280f9e9f70c8",
                "-o",
                "jsonpath={.items[0].metadata.name}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        actual_pod_name = result.stdout.strip()
        print(f"   Actual pod name: {actual_pod_name}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to get pod name: {e}")
        return

    environment_id = "68850093852e1ff1492d3d87"

    # Get current environment data
    async with httpx.AsyncClient() as client:
        print(f"📋 Getting current environment data...")
        response = await client.get(
            f"https://devpocket-api.goon.vn/api/v1/environments/{environment_id}",
            headers=headers,
            timeout=30,
        )

        if response.status_code == 200:
            env_data = response.json()
            print(f"   Current environment: {env_data.get('name')}")
            print(f"   Current namespace: {env_data.get('namespace')}")
            print(f"   Current pod_name: {env_data.get('pod_name')}")

            # Update with correct data
            update_data = {
                "namespace": "user-6880cb54f9f0280f9e9f70c8",
                "pod_name": actual_pod_name,  # Use the full pod name
            }

            print(f"\n🔧 Updating environment with:")
            print(f"   Namespace: {update_data['namespace']}")
            print(f"   Pod name: {update_data['pod_name']}")

            # Note: The API doesn't have a direct update endpoint,
            # so this would need to be done via database access
            print("\n⚠️ This update needs to be done via direct database access.")
            print("The API doesn't expose an environment update endpoint.")

            return update_data
        else:
            print(
                f"❌ Failed to get environment: {response.status_code} - {response.text}"
            )
            return None


async def main():
    """Main function"""
    print("🚀 Fixing Production Environment Data")
    print("=" * 50)

    update_data = await fix_production_environment()

    if update_data:
        print("\n" + "=" * 50)
        print("💡 To fix this, run the following MongoDB update command:")
        print("db.environments.updateOne(")
        print('  {"_id": ObjectId("68850093852e1ff1492d3d87")},')
        print(
            f'  {{"$set": {{"namespace": "{update_data["namespace"]}", "pod_name": "{update_data["pod_name"]}"}}}}'
        )
        print(")")


if __name__ == "__main__":
    asyncio.run(main())
