#!/usr/bin/env python3
"""
Add kubeconfig to cluster record in production database.
"""

import asyncio
import base64
import os

from bson import ObjectId
from cryptography.fernet import Fernet
from motor.motor_asyncio import AsyncIOMotorClient


async def add_kubeconfig_to_production():
    """Add kubeconfig to production cluster"""

    # Production MongoDB connection
    mongodb_url = "mongodb://devpocket:devpocket@devpocket-api.goon.vn:27017"
    database_name = "devpocket"

    # Use the same encryption key as the application
    secret_key = os.getenv("SECRET_KEY", "9XX36cij9crf1VJPFUjphfZlk8vfuOBok5pxkHa-YsU")
    encryption_key = secret_key[:32].ljust(32, "0").encode()[:32]
    cipher_suite = Fernet(base64.urlsafe_b64encode(encryption_key))

    print(f"🔌 Connecting to production MongoDB...")

    try:
        # Connect to database
        client = AsyncIOMotorClient(mongodb_url)
        db = client[database_name]

        # Read the kubeconfig file
        kubeconfig_path = "k8s/kube_config_ovh.yaml"
        if not os.path.exists(kubeconfig_path):
            print(f"❌ Kubeconfig file not found: {kubeconfig_path}")
            return False

        with open(kubeconfig_path, "r") as f:
            kubeconfig_content = f.read()

        print(f"📄 Read kubeconfig file: {len(kubeconfig_content)} characters")

        # Encode to base64 (this is what get_decrypted_kubeconfig expects)
        kubeconfig_b64 = base64.b64encode(kubeconfig_content.encode("utf-8")).decode(
            "utf-8"
        )
        print(f"🔐 Base64 encoded kubeconfig: {len(kubeconfig_b64)} characters")

        # Encrypt the base64-encoded kubeconfig
        encrypted_config = cipher_suite.encrypt(kubeconfig_b64.encode()).decode()
        print(f"🔒 Encrypted kubeconfig: {len(encrypted_config)} characters")

        # Find the cluster
        cluster_id = ObjectId("6880c50bb1e35403dc11f69c")
        cluster = await db.clusters.find_one({"_id": cluster_id})

        if not cluster:
            print(f"❌ Cluster not found: {cluster_id}")
            return False

        print(f"✅ Found cluster: {cluster.get('name')} ({cluster.get('region')})")
        print(
            f"   Current encrypted_kube_config exists: {'encrypted_kube_config' in cluster}"
        )

        # Update cluster with encrypted kubeconfig
        result = await db.clusters.update_one(
            {"_id": cluster_id}, {"$set": {"encrypted_kube_config": encrypted_config}}
        )

        if result.modified_count > 0:
            print("✅ Encrypted kubeconfig updated successfully")

            # Verify the update by decrypting
            updated_cluster = await db.clusters.find_one({"_id": cluster_id})
            if "encrypted_kube_config" in updated_cluster:
                print(
                    f"   Encrypted kubeconfig field updated with {len(updated_cluster['encrypted_kube_config'])} characters"
                )

                # Test decryption
                try:
                    decrypted = cipher_suite.decrypt(
                        updated_cluster["encrypted_kube_config"].encode()
                    ).decode()
                    decoded = base64.b64decode(decrypted).decode("utf-8")
                    print(
                        f"   ✅ Test decryption successful - kubeconfig is {len(decoded)} characters"
                    )
                    return True
                except Exception as e:
                    print(f"   ❌ Test decryption failed: {e}")
                    return False
            else:
                print("❌ encrypted_kube_config field not found after update")
                return False
        else:
            print("⚠️ No changes made - encrypted_kube_config may already be correct")

            # Test existing encrypted_kube_config
            if "encrypted_kube_config" in cluster:
                try:
                    decrypted = cipher_suite.decrypt(
                        cluster["encrypted_kube_config"].encode()
                    ).decode()
                    decoded = base64.b64decode(decrypted).decode("utf-8")
                    print(
                        f"   ✅ Existing encrypted_kube_config is valid - {len(decoded)} characters"
                    )
                    return True
                except Exception as e:
                    print(f"   ❌ Existing encrypted_kube_config is invalid: {e}")
                    return False
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        if "client" in locals():
            client.close()


if __name__ == "__main__":
    success = asyncio.run(add_kubeconfig_to_production())
    if success:
        print("\n🎉 Kubeconfig successfully encrypted and added to production cluster!")
        print("Now the get_actual_pod_name() method should work correctly.")
    else:
        print("\n❌ Failed to add encrypted kubeconfig to cluster.")
