#!/usr/bin/env python3
"""
Load default templates from YAML files

This script loads environment templates from YAML files in the scripts/templates directory
and seeds them into the database. This replaces the hardcoded template definitions.

Usage:
    python3 scripts/load_templates.py

Or run with production environment:
    ENV_FILE=.env.prod python3 scripts/load_templates.py
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

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


def load_template_files() -> List[Dict[str, Any]]:
    """Load all template YAML files from scripts/templates directory"""
    templates_dir = Path(__file__).parent / "templates"
    templates = []

    if not templates_dir.exists():
        logger.error(f"Templates directory not found: {templates_dir}")
        return templates

    # Load all YAML files
    for yaml_file in templates_dir.glob("*.yaml"):
        try:
            with open(yaml_file, "r") as f:
                template_data = yaml.safe_load(f)
                templates.append(template_data)
                logger.info(
                    f"Loaded template from {yaml_file.name}: {template_data['name']}"
                )
        except Exception as e:
            logger.error(f"Error loading template from {yaml_file}: {e}")

    logger.info(f"Loaded {len(templates)} templates from YAML files")
    return templates


async def seed_templates_from_files():
    """Seed templates from YAML files into the database"""

    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    # Initialize template service
    template_service.set_database(db)

    try:
        logger.info("Starting template seeding from YAML files...")

        # Load templates from YAML files
        template_data_list = load_template_files()

        if not template_data_list:
            logger.error("No templates found in YAML files")
            return

        # Check existing templates count
        existing_count = await db.templates.count_documents({})
        logger.info(f"Found {existing_count} existing templates")

        if existing_count > 0:
            logger.info("Templates already exist. Use --force to reseed.")
            return

        # Seed each template
        created_count = 0
        for template_data in template_data_list:
            try:
                # Convert to the format expected by template service
                await template_service.create_template_from_data(template_data)
                created_count += 1
                logger.info(f"Created template: {template_data['name']}")
            except Exception as e:
                logger.error(f"Error creating template {template_data['name']}: {e}")

        # Verify templates were created
        final_count = await db.templates.count_documents({})
        logger.info(
            f"Successfully seeded {created_count} templates (total: {final_count})"
        )

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


async def force_reseed_templates_from_files():
    """Force reseed templates from YAML files (removes existing ones first)"""

    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    # Initialize template service
    template_service.set_database(db)

    try:
        logger.info("Force reseeding templates from YAML files...")

        # Load templates from YAML files
        template_data_list = load_template_files()

        if not template_data_list:
            logger.error("No templates found in YAML files")
            return

        # Remove existing templates
        result = await db.templates.delete_many({})
        logger.info(f"Removed {result.deleted_count} existing templates")

        # Seed each template
        created_count = 0
        for template_data in template_data_list:
            try:
                # Convert to the format expected by template service
                await template_service.create_template_from_data(template_data)
                created_count += 1
                logger.info(f"Created template: {template_data['name']}")
            except Exception as e:
                logger.error(f"Error creating template {template_data['name']}: {e}")

        # Verify templates were created
        final_count = await db.templates.count_documents({})
        logger.info(
            f"Successfully reseeded {created_count} templates (total: {final_count})"
        )

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

    parser = argparse.ArgumentParser(
        description="Seed environment templates from YAML files"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reseed (remove existing templates first)",
    )

    args = parser.parse_args()

    if args.force:
        asyncio.run(force_reseed_templates_from_files())
    else:
        asyncio.run(seed_templates_from_files())


if __name__ == "__main__":
    main()
