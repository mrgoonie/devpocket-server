#!/usr/bin/env python3
"""
Test script for resilient startup functionality
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.environment import EnvironmentTemplate
from app.services.environment_service import EnvironmentService


def test_resilient_startup_script():
    """Test the resilient startup script generation"""
    service = EnvironmentService()

    # Test commands with critical and optional components
    test_commands = [
        "apt-get update",
        "apt-get install -y sudo curl wget git vim nano",
        "useradd -m -s /bin/bash devpocket",
        "echo 'devpocket:devpocket' | chpasswd",
        "usermod -aG sudo devpocket",
        "echo 'devpocket ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers",
        "mkdir -p /home/devpocket/workspace",
        "chown -R devpocket:devpocket /home/devpocket",
        "npm install -g @some/nonexistent-package",  # This should fail gracefully
        "pip3 install some-fake-package",  # This should fail gracefully
        "curl -f https://invalid-url.com/script.sh",  # This should fail gracefully
    ]

    # Generate resilient script
    startup_command = service._create_resilient_startup_script(test_commands)

    print("Generated Resilient Startup Command:")
    print("=" * 50)

    # Decode and format the script for readability
    if "echo $'" in startup_command and "' > /tmp/init.sh" in startup_command:
        script_content = startup_command.split("echo $'")[1].split("' > /tmp/init.sh")[
            0
        ]
        script_lines = script_content.replace("\\n", "\n")
        print(script_lines)
    else:
        print("Raw command:")
        print(
            startup_command[:500] + "..."
            if len(startup_command) > 500
            else startup_command
        )

    print("\n" + "=" * 50)
    print("Key Features of the Resilient Script:")
    print("- Critical commands (user setup) must succeed or container exits")
    print("- Optional commands (packages) can fail without stopping container")
    print("- All failures are logged to /var/log/devpocket-init.log")
    print("- Status file created at /tmp/devpocket-status for health checks")
    print("- Container always stays running with 'sleep infinity'")


if __name__ == "__main__":
    test_resilient_startup_script()
