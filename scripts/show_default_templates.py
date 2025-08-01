#!/usr/bin/env python3
"""
Show default environment templates that would be seeded.
This script displays the default templates without requiring a database connection.

Usage:
    python3 scripts/show_default_templates.py

Or run with production environment:
    ENV_FILE=.env.prod python3 scripts/show_default_templates.py
"""

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


async def show_default_templates():
    """Display default templates from YAML files"""
    import yaml

    # Load templates from YAML files
    templates_dir = Path(__file__).parent / "templates"
    default_templates = []

    if not templates_dir.exists():
        print(f"Templates directory not found: {templates_dir}")
        return

    # Load all YAML files
    for yaml_file in templates_dir.glob("*.yaml"):
        try:
            with open(yaml_file, "r") as f:
                template_data = yaml.safe_load(f)
                default_templates.append(template_data)
        except Exception as e:
            print(f"Error loading template from {yaml_file}: {e}")

    if not default_templates:
        print("No templates found in YAML files")
        return

    print(f"Default Templates ({len(default_templates)}):")
    print("=" * 50)

    for template in default_templates:
        print(f"\n📦 {template['name']}")
        print(f"   Display: {template['display_name']}")
        print(f"   Category: {template['category']}")
        print(f"   Description: {template['description']}")
        print(f"   Docker Image: {template['docker_image']}")
        print(f"   Default Port: {template['default_port']}")
        print(f"   Resources: {template['default_resources']}")
        print(f"   Tags: {', '.join(template['tags'])}")

        if template.get("environment_variables"):
            print(f"   Environment Variables:")
            for key, value in template["environment_variables"].items():
                print(f"     {key}: {value}")

        if template.get("startup_commands"):
            print(f"   Startup Commands:")
            for cmd in template["startup_commands"]:
                print(f"     - {cmd}")

        if template.get("documentation_url"):
            print(f"   Documentation: {template['documentation_url']}")


def main():
    """Main script entry point"""
    import asyncio

    asyncio.run(show_default_templates())


if __name__ == "__main__":
    main()
