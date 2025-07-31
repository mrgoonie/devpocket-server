#!/usr/bin/env python3
"""
Debug script to check cluster configuration
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
    from motor.motor_asyncio import AsyncIOMotorClient

    from app.core.config import settings
    from app.models.cluster import ClusterRegion
    from app.services.cluster_service import cluster_service
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


async def debug_cluster():
    """Debug cluster configuration"""

    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    # Initialize cluster service
    cluster_service.set_database(db)

    # List all clusters
    print("🔍 Debugging cluster configuration...")
    print(f"Database: {settings.DATABASE_NAME}")
    print(f"MongoDB URL: {settings.MONGODB_URL}")

    # Check raw data in database
    print("\n📋 Raw cluster data in database:")
    cursor = db.clusters.find({})
    async for cluster_doc in cursor:
        print(f"   Cluster: {cluster_doc.get('name', 'Unknown')}")
        print(f"   Region: {cluster_doc.get('region', 'Unknown')}")
        print(f"   Status: {cluster_doc.get('status', 'Unknown')}")
        print(f"   Is Default: {cluster_doc.get('is_default', False)}")
        print(f"   Has encrypted_kube_config: {'encrypted_kube_config' in cluster_doc}")
        if "encrypted_kube_config" in cluster_doc:
            config_length = len(cluster_doc["encrypted_kube_config"])
            print(f"   Config length: {config_length} chars")
        print()

    # Try to get cluster by region
    print("🔍 Trying to get cluster by region...")
    cluster = await cluster_service.get_cluster_by_region(ClusterRegion.SOUTHEAST_ASIA)
    if cluster:
        print(f"✅ Found cluster: {cluster.name}")
        print(f"   ID: {cluster.id}")
        print(f"   Region: {cluster.region}")
        print(f"   Status: {cluster.status}")

        # Try to get kubeconfig
        print("\n🔑 Trying to get kubeconfig...")
        kubeconfig = await cluster_service.get_decrypted_kubeconfig(cluster.id)
        if kubeconfig:
            print(f"✅ Successfully retrieved kubeconfig ({len(kubeconfig)} chars)")
        else:
            print("❌ Failed to get kubeconfig")
    else:
        print("❌ No cluster found for Southeast Asia region")

    client.close()


if __name__ == "__main__":
    try:
        asyncio.run(debug_cluster())
    except Exception as e:
        print(f"💥 Error: {str(e)}")
        import traceback

        traceback.print_exc()
