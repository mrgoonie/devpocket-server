#!/usr/bin/env python3
"""
Update environment status to running for testing
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
    from app.core.config import settings
    from datetime import datetime
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


async def update_environment_status():
    """Update environment status to running"""
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]
    
    print("🔍 Looking for environments to update...")
    
    # Find environments that are creating
    cursor = db.environments.find({
        "user_id": "c1e89f47-f92c-4dea-91bf-d8cfcc54cf47"
    })
    
    environments = []
    async for env_doc in cursor:
        environments.append(env_doc)
        print(f"📋 Environment: {env_doc['name']} - Status: {env_doc['status']}")
    
    if not environments:
        print("❌ No environments found")
        client.close()
        return
    
    # Update the latest environment to running
    latest_env = max(environments, key=lambda x: x['created_at'])
    env_id = latest_env['_id']
    env_name = latest_env['name']
    
    print(f"\n🎯 Updating environment: {env_name} ({env_id})")
    
    # Update status to running
    result = await db.environments.update_one(
        {"_id": env_id},
        {
            "$set": {
                "status": "running",
                "external_url": f"https://env-{latest_env['pod_name']}.devpocket.io",
                "internal_url": f"http://{latest_env['service_name']}.{latest_env['namespace']}.svc.cluster.local:8080",
                "web_port": 8080,
                "ssh_port": 22,
                "updated_at": datetime.utcnow(),
            }
        }
    )
    
    if result.modified_count > 0:
        print(f"✅ Successfully updated {env_name} to running status")
        print(f"🌐 External URL: https://env-{latest_env['pod_name']}.devpocket.io")
        print(f"🔗 Internal URL: http://{latest_env['service_name']}.{latest_env['namespace']}.svc.cluster.local:8080")
    else:
        print(f"❌ Failed to update environment status")
    
    client.close()


if __name__ == "__main__":
    try:
        asyncio.run(update_environment_status())
    except Exception as e:
        print(f"💥 Error: {str(e)}")
        sys.exit(1)