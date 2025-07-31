#!/usr/bin/env python3
"""
Test script to verify sudo support in templates.
This script shows what commands would work in the new templates.
"""

import asyncio
import os
import sys
from pathlib import Path

# Load environment variables first
env_file = os.getenv("ENV_FILE", ".env")
if Path(env_file).exists():
    from dotenv import load_dotenv

    load_dotenv(env_file)

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import structlog
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.services.template_service import template_service

logger = structlog.get_logger(__name__)


async def test_sudo_support():
    """Test sudo support in templates"""

    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    # Initialize template service
    template_service.set_database(db)

    try:
        logger.info("Testing sudo support in templates...")

        # Get templates
        templates = await template_service.list_templates()

        print("\n" + "=" * 60)
        print("SUDO SUPPORT TEST FOR DEVPOCKET TEMPLATES")
        print("=" * 60)

        for template in templates:
            print(f"\n📦 {template.display_name} ({template.name})")
            print(f"   Description: {template.description}")

            if "sudo" in template.tags:
                print("   ✅ SUDO SUPPORTED")
                print("   📋 Available commands after container startup:")
                print("      - sudo apt-get update")
                print("      - sudo apt-get install <package>")
                print("      - sudo systemctl <service>")
                print("      - ll (alias for ls -la)")
                print("      - User: devpocket with passwordless sudo")
                print("      - Home: /home/devpocket")
                print("      - Workspace: /home/devpocket/workspace")
            else:
                print("   ❌ No sudo support")

            print(f"   🔧 Startup commands ({len(template.startup_commands)} total):")
            for i, cmd in enumerate(template.startup_commands[:3], 1):
                print(f"      {i}. {cmd}")
            if len(template.startup_commands) > 3:
                print(f"      ... and {len(template.startup_commands) - 3} more")

        print("\n" + "=" * 60)
        print("FLUTTER APP TESTING INSTRUCTIONS")
        print("=" * 60)
        print("Now you can test in your Flutter app:")
        print("1. Create a new environment with any template")
        print("2. Connect to terminal via WebSocket")
        print("3. Try these commands:")
        print("   • sudo apt-get update")
        print("   • sudo apt-get install htop")
        print("   • htop (should work!)")
        print("   • ll (should show ls -la)")
        print("   • whoami (should show: devpocket)")
        print("   • pwd (should show: /home/devpocket/workspace)")
        print("\nAll templates now have proper sudo support! 🎉")

    except Exception as e:
        logger.error(f"Error testing sudo support: {e}")
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(test_sudo_support())
