#!/usr/bin/env python3
"""
Script to add the default OVH Kubernetes cluster to the DevPocket database.
This cluster is located in Southeast Asia region and will be set as the default cluster for that region.

Usage:
    python scripts/add_default_ovh_cluster.py

Or run with production environment:
    ENV_FILE=.env.prod python scripts/add_default_ovh_cluster.py
"""

import asyncio
import base64
import os
import sys
from pathlib import Path

# Load environment variables first
env_file = os.getenv("ENV_FILE", ".env")
if Path(env_file).exists():
    from dotenv import load_dotenv

    load_dotenv(env_file)

# Add the app directory to Python path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

try:
    from motor.motor_asyncio import AsyncIOMotorClient

    from app.core.config import settings
    from app.models.cluster import ClusterCreate, ClusterRegion
    from app.services.cluster_service import ClusterService
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure you have installed the required dependencies:")
    print("pip install motor pymongo cryptography pyyaml structlog python-dotenv")
    sys.exit(1)


async def add_ovh_cluster():
    """Add the OVH cluster configuration to the database"""

    # Read the kubeconfig file
    kubeconfig_path = app_dir / "k8s" / "kube_config_ovh.yaml"

    if not kubeconfig_path.exists():
        print(f"Error: Kubeconfig file not found at {kubeconfig_path}")
        return False

    try:
        with open(kubeconfig_path, "r") as f:
            kubeconfig_content = f.read()

        # Encode kubeconfig to base64
        kubeconfig_b64 = base64.b64encode(kubeconfig_content.encode()).decode()

        # Create cluster data
        cluster_data = ClusterCreate(
            name="ovh-southeast-asia",
            region=ClusterRegion.SOUTHEAST_ASIA,
            description="OVH Kubernetes cluster in Southeast Asia region - Default cluster",
            endpoint="https://51.79.231.184:16443",
            is_default=True,
            max_environments=500,
            kube_config=kubeconfig_b64,
        )

        # Connect to MongoDB
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        db = client[settings.DATABASE_NAME]

        # Initialize cluster service
        cluster_service = ClusterService()
        cluster_service.set_database(db)

        # Check if cluster already exists
        existing_cluster = await db.clusters.find_one({"name": cluster_data.name})
        if existing_cluster:
            print(f"Cluster '{cluster_data.name}' already exists!")
            print(f"Current status: {existing_cluster.get('status', 'unknown')}")
            print(f"Region: {existing_cluster.get('region', 'unknown')}")
            print(f"Is default: {existing_cluster.get('is_default', False)}")

            # Check if running non-interactively
            force_update = os.getenv("FORCE_UPDATE", "").lower() in ("true", "1", "yes")
            if force_update:
                print("Force update enabled. Updating existing cluster...")
            else:
                # Ask if user wants to update
                try:
                    response = input(
                        "Do you want to update the existing cluster? (y/N): "
                    ).strip()
                    if response.lower() not in ("y", "yes"):
                        print("Operation cancelled.")
                        client.close()
                        return True
                except EOFError:
                    print("Non-interactive mode detected. Skipping update.")
                    print("Use FORCE_UPDATE=true to force update.")
                    client.close()
                    return True

            # Update existing cluster
            await db.clusters.update_one(
                {"name": cluster_data.name},
                {
                    "$set": {
                        "description": cluster_data.description,
                        "endpoint": cluster_data.endpoint,
                        "is_default": cluster_data.is_default,
                        "max_environments": cluster_data.max_environments,
                        "region": cluster_data.region,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
            print(f"Cluster '{cluster_data.name}' updated successfully!")
        else:
            # Create new cluster
            created_cluster = await cluster_service.create_cluster(
                cluster_data,
                # created_by will default to SYSTEM_USER_ID
            )

            print(f"✅ Successfully added OVH cluster:")
            print(f"   Name: {created_cluster.name}")
            print(f"   Region: {created_cluster.region}")
            print(f"   Endpoint: {created_cluster.endpoint}")
            print(f"   Is Default: {created_cluster.is_default}")
            print(f"   Max Environments: {created_cluster.max_environments}")
            print(f"   Status: {created_cluster.status}")
            print(f"   Created: {created_cluster.created_at}")

        # Close connection
        client.close()
        return True

    except Exception as e:
        print(f"❌ Error adding OVH cluster: {str(e)}")
        return False


async def verify_cluster():
    """Verify the cluster was added successfully"""
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        db = client[settings.DATABASE_NAME]

        # Initialize cluster service
        cluster_service = ClusterService()
        cluster_service.set_database(db)

        # Get cluster by region
        cluster = await cluster_service.get_cluster_by_region(
            ClusterRegion.SOUTHEAST_ASIA
        )

        if cluster:
            print(f"\n✅ Verification successful:")
            print(f"   Default cluster for Southeast Asia: {cluster.name}")
            print(f"   Status: {cluster.status}")
            print(f"   Endpoint: {cluster.endpoint}")
            print(f"   Max Environments: {cluster.max_environments}")
        else:
            print("❌ No cluster found for Southeast Asia region")

        # List all clusters
        all_clusters = await cluster_service.list_clusters()
        print(f"\n📋 Total clusters in database: {len(all_clusters)}")
        for cluster in all_clusters:
            default_marker = (
                " [DEFAULT]"
                if hasattr(cluster, "is_default") and cluster.is_default
                else ""
            )
            print(f"   • {cluster.name} ({cluster.region}){default_marker}")

        client.close()

    except Exception as e:
        print(f"❌ Verification failed: {str(e)}")


async def main():
    """Main function"""
    print("🚀 Adding OVH Kubernetes cluster to DevPocket...")
    print(f"📁 Using kubeconfig from: k8s/kube_config_ovh.yaml")
    print(
        f"🗄️  Database: {settings.MONGODB_URL.split('@')[-1] if '@' in settings.MONGODB_URL else settings.MONGODB_URL}"
    )
    print()

    success = await add_ovh_cluster()

    if success:
        print("\n🔍 Verifying cluster configuration...")
        await verify_cluster()
        print("\n✅ Setup completed successfully!")
        print(
            "\nUsers can now select the Southeast Asia region when creating environments."
        )
    else:
        print("\n❌ Setup failed!")
        sys.exit(1)


if __name__ == "__main__":
    # Import datetime here to avoid circular imports
    from datetime import datetime

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)
