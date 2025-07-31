#!/usr/bin/env python3
"""Verify sudo support in default environment templates"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.template_service import template_service


async def verify_sudo_support():
    """Check if all templates have proper sudo setup commands"""
    print("Verifying sudo support in default templates...\n")

    templates = await template_service.get_default_templates()

    sudo_commands_to_check = [
        "sudo",  # Check if sudo package is installed
        "devpocket ALL=(ALL) NOPASSWD:ALL",  # Check sudoers configuration
    ]

    all_good = True

    for template in templates:
        print(f"Template: {template['display_name']} ({template['name']})")
        print("-" * 50)

        startup_commands = template.get("startup_commands", [])
        all_commands_text = " ".join(startup_commands)

        has_sudo_support = True
        missing_items = []

        for cmd in sudo_commands_to_check:
            if cmd not in all_commands_text:
                has_sudo_support = False
                missing_items.append(cmd)

        # Check for either sudo or wheel group (for CentOS)
        has_group_assignment = (
            "usermod -aG sudo devpocket" in all_commands_text
            or "usermod -aG wheel devpocket" in all_commands_text
        )

        if not has_group_assignment:
            has_sudo_support = False
            missing_items.append("usermod -aG sudo/wheel devpocket")

        if has_sudo_support:
            print("✅ Has sudo support")
            # Show relevant commands
            sudo_related = [
                cmd
                for cmd in startup_commands
                if "sudo" in cmd.lower() or "devpocket" in cmd
            ]
            if sudo_related:
                print("   Sudo-related commands:")
                for cmd in sudo_related[:5]:  # Show first 5 relevant commands
                    print(f"   - {cmd}")
        else:
            print("❌ Missing sudo support")
            print(f"   Missing: {', '.join(missing_items)}")
            all_good = False

        # Check if template has 'sudo' tag
        if "sudo" in template.get("tags", []):
            print("✅ Has 'sudo' tag")
        else:
            print("⚠️  Missing 'sudo' tag")

        print()

    # Also check the environment service container creation
    print("\nChecking environment service container creation:")
    print("-" * 50)

    # Read the environment service file
    env_service_path = (
        Path(__file__).parent.parent / "app" / "services" / "environment_service.py"
    )
    if env_service_path.exists():
        with open(env_service_path, "r") as f:
            content = f.read()

        # Find the container creation command
        if "devpocket ALL=(ALL) NOPASSWD:ALL" in content:
            print("✅ Environment service has sudo setup for devpocket user")
        else:
            print("❌ Environment service missing proper sudo setup")
            all_good = False

        if "useradd -m -s /bin/bash devpocket" in content:
            print("✅ Environment service creates devpocket user")
        else:
            print("❌ Environment service doesn't create devpocket user")
            all_good = False
    else:
        print("❌ Could not find environment_service.py")
        all_good = False

    print("\n" + "=" * 50)
    if all_good:
        print("✅ All templates have proper sudo support!")
    else:
        print("❌ Some templates are missing sudo support.")

    return all_good


if __name__ == "__main__":
    result = asyncio.run(verify_sudo_support())
    sys.exit(0 if result else 1)
