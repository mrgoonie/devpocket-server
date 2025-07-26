#!/usr/bin/env python3
"""
Seed default environment templates into the database.
This script initializes the templates collection with default programming language templates.

Usage:
    python3 scripts/seed_templates.py

Or run with production environment:
    ENV_FILE=.env.prod python3 scripts/seed_templates.py
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


async def seed_templates():
    """Seed default templates into the database"""

    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    # Initialize template service
    template_service.set_database(db)

    try:
        logger.info("Starting template seeding process...")

        # Check existing templates count
        existing_count = await db.templates.count_documents({})
        logger.info(f"Found {existing_count} existing templates")

        if existing_count > 0:
            logger.info("Templates already exist. Use --force to reseed.")
            return

        # Initialize default templates
        await template_service.initialize_default_templates()

        # Verify templates were created
        final_count = await db.templates.count_documents({})
        logger.info(f"Successfully seeded {final_count} templates")

        # List created templates
        templates = await template_service.list_templates()
        logger.info("Created templates:")
        for template in templates:
            logger.info(f"  - {template.name}: {template.display_name}")

    except Exception as e:
        logger.error(f"Error seeding templates: {e}")
        sys.exit(1)
    finally:
        client.close()


async def force_reseed_templates():
    """Force reseed templates (removes existing ones first)"""

    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    # Initialize template service
    template_service.set_database(db)

    try:
        logger.info("Force reseeding templates...")

        # Remove existing templates
        result = await db.templates.delete_many({})
        logger.info(f"Removed {result.deleted_count} existing templates")

        # Initialize default templates
        await template_service.initialize_default_templates()

        # Verify templates were created
        final_count = await db.templates.count_documents({})
        logger.info(f"Successfully reseeded {final_count} templates")

        # List created templates
        templates = await template_service.list_templates()
        logger.info("Reseeded templates:")
        for template in templates:
            logger.info(f"  - {template.name}: {template.display_name}")

    except Exception as e:
        logger.error(f"Error reseeding templates: {e}")
        sys.exit(1)
    finally:
        client.close()


def main():
    """Main script entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Seed default environment templates")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reseed (remove existing templates first)",
    )

    args = parser.parse_args()

    if args.force:
        asyncio.run(force_reseed_templates())
    else:
        asyncio.run(seed_templates())


if __name__ == "__main__":
    main()
