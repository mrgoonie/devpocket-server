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
    """Display default templates"""
    # Get the raw template data instead of TemplateInDB objects
    default_templates = [
        {
            "name": "coding-agent",
            "display_name": "Coding Agent (Ubuntu + AI Tools)",
            "description": "Ubuntu environment with AI coding tools pre-installed including Claude Code, Gemini CLI, Qwen Code and Open Code. Perfect for AI-assisted development with sudo access.",
            "category": "programming_language",
            "tags": [
                "ubuntu",
                "linux",
                "ai",
                "claude-code",
                "gemini",
                "qwen",
                "coding-assistant",
                "development",
                "sudo",
            ],
            "docker_image": "ubuntu:22.04",
            "default_port": 8080,
            "default_resources": {"cpu": "1000m", "memory": "2Gi", "storage": "20Gi"},
            "environment_variables": {
                "DEBIAN_FRONTEND": "noninteractive",
                "TERM": "xterm-256color",
                "USER": "devpocket",
                "HOME": "/home/devpocket",
                "PATH": "/home/devpocket/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            },
            "startup_commands": [
                "apt-get update",
                "apt-get install -y sudo curl wget git vim nano build-essential software-properties-common apt-transport-https ca-certificates gnupg lsb-release python3 python3-pip nodejs npm",
                "useradd -m -s /bin/bash devpocket",
                "echo 'devpocket:devpocket' | chpasswd",
                "usermod -aG sudo devpocket",
                "echo 'devpocket ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers",
                "mkdir -p /home/devpocket/workspace /home/devpocket/.local/bin",
                "chown -R devpocket:devpocket /home/devpocket",
                "su - devpocket -c 'curl -fsSL https://claude.ai/cli/install.sh | bash'",
                "su - devpocket -c 'npm install -g @google/generative-ai-cli'",
                "su - devpocket -c 'pip3 install --user qwencoder-cli'",
                "wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg",
                "install -o root -g root -m 644 packages.microsoft.gpg /etc/apt/trusted.gpg.d/",
                "echo 'deb [arch=amd64,arm64,armhf signed-by=/etc/apt/trusted.gpg.d/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main' > /etc/apt/sources.list.d/vscode.list",
                "apt-get update",
                "apt-get install -y code",
            ],
            "documentation_url": "https://claude.ai/code",
            "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/ubuntu/ubuntu-plain.svg",
        },
        {
            "name": "ubuntu",
            "display_name": "Ubuntu 22.04 LTS",
            "description": "Ubuntu environment with sudo access and essential development tools. Includes a non-root user with sudo privileges for package installation and system management.",
            "category": "operating_system",
            "tags": ["ubuntu", "linux", "bash", "shell", "development", "sudo"],
            "docker_image": "ubuntu:22.04",
            "default_port": 8080,
            "default_resources": {"cpu": "500m", "memory": "1Gi", "storage": "10Gi"},
            "environment_variables": {
                "DEBIAN_FRONTEND": "noninteractive",
                "TERM": "xterm-256color",
                "USER": "devpocket",
                "HOME": "/home/devpocket",
            },
            "startup_commands": [
                "apt-get update",
                "apt-get install -y sudo curl wget git vim nano build-essential software-properties-common apt-transport-https ca-certificates gnupg lsb-release unzip tar gzip",
                "useradd -m -s /bin/bash devpocket",
                "echo 'devpocket:devpocket' | chpasswd",
                "usermod -aG sudo devpocket",
                "echo 'devpocket ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers",
                "mkdir -p /home/devpocket/workspace",
                "chown -R devpocket:devpocket /home/devpocket",
            ],
            "documentation_url": "https://ubuntu.com/server/docs",
            "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/ubuntu/ubuntu-plain.svg",
        },
        {
            "name": "centos",
            "display_name": "CentOS Stream 9",
            "description": "CentOS environment with sudo access and essential development tools. Includes a non-root user with sudo privileges for package installation and system management.",
            "category": "operating_system",
            "tags": [
                "centos",
                "linux",
                "bash",
                "shell",
                "development",
                "sudo",
                "redhat",
            ],
            "docker_image": "quay.io/centos/centos:stream9",
            "default_port": 8080,
            "default_resources": {"cpu": "500m", "memory": "1Gi", "storage": "10Gi"},
            "environment_variables": {
                "TERM": "xterm-256color",
                "USER": "devpocket",
                "HOME": "/home/devpocket",
            },
            "startup_commands": [
                "dnf update -y",
                "dnf groupinstall -y 'Development Tools'",
                "dnf install -y sudo curl wget git vim nano unzip tar gzip which",
                "useradd -m -s /bin/bash devpocket",
                "echo 'devpocket:devpocket' | chpasswd",
                "usermod -aG wheel devpocket",
                "echo 'devpocket ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers",
                "mkdir -p /home/devpocket/workspace",
                "chown -R devpocket:devpocket /home/devpocket",
            ],
            "documentation_url": "https://docs.centos.org/",
            "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/centos/centos-original.svg",
        },
        {
            "name": "debian",
            "display_name": "Debian 12 (Bookworm)",
            "description": "Debian environment with sudo access and essential development tools. Includes a non-root user with sudo privileges for package installation and system management.",
            "category": "operating_system",
            "tags": ["debian", "linux", "bash", "shell", "development", "sudo"],
            "docker_image": "debian:12",
            "default_port": 8080,
            "default_resources": {"cpu": "500m", "memory": "1Gi", "storage": "10Gi"},
            "environment_variables": {
                "DEBIAN_FRONTEND": "noninteractive",
                "TERM": "xterm-256color",
                "USER": "devpocket",
                "HOME": "/home/devpocket",
            },
            "startup_commands": [
                "apt-get update",
                "apt-get install -y sudo curl wget git vim nano build-essential software-properties-common apt-transport-https ca-certificates gnupg unzip tar gzip",
                "useradd -m -s /bin/bash devpocket",
                "echo 'devpocket:devpocket' | chpasswd",
                "usermod -aG sudo devpocket",
                "echo 'devpocket ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers",
                "mkdir -p /home/devpocket/workspace",
                "chown -R devpocket:devpocket /home/devpocket",
            ],
            "documentation_url": "https://www.debian.org/doc/",
            "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/debian/debian-original.svg",
        },
        {
            "name": "nodejs",
            "display_name": "Node.js 18 LTS",
            "description": "Node.js development environment with npm, yarn, and popular packages. Includes sudo access for system package installation and essential development tools.",
            "category": "programming_language",
            "tags": [
                "nodejs",
                "npm",
                "yarn",
                "express",
                "react",
                "vue",
                "javascript",
                "sudo",
            ],
            "docker_image": "node:18-slim",
            "default_port": 3000,
            "default_resources": {"cpu": "500m", "memory": "1Gi", "storage": "10Gi"},
            "environment_variables": {
                "NODE_ENV": "development",
                "npm_config_cache": "/tmp/npm-cache",
                "DEBIAN_FRONTEND": "noninteractive",
                "USER": "devpocket",
                "HOME": "/home/devpocket",
            },
            "startup_commands": [
                "apt-get update",
                "apt-get install -y sudo curl wget git vim nano build-essential unzip tar gzip",
                "useradd -m -s /bin/bash devpocket",
                "echo 'devpocket:devpocket' | chpasswd",
                "usermod -aG sudo devpocket",
                "echo 'devpocket ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers",
                "mkdir -p /home/devpocket/workspace",
                "chown -R devpocket:devpocket /home/devpocket",
                "su - devpocket -c 'npm install -g nodemon typescript @types/node yarn'",
            ],
            "documentation_url": "https://nodejs.org/en/docs/",
            "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/nodejs/nodejs-original.svg",
        },
        {
            "name": "python",
            "display_name": "Python 3.11",
            "description": "Python development environment with pip, virtualenv, and common packages pre-installed. Includes sudo access for system package installation and essential development tools.",
            "category": "programming_language",
            "tags": [
                "python",
                "python3",
                "pip",
                "virtualenv",
                "flask",
                "django",
                "sudo",
            ],
            "docker_image": "python:3.11-slim",
            "default_port": 8080,
            "default_resources": {"cpu": "500m", "memory": "1Gi", "storage": "10Gi"},
            "environment_variables": {
                "PYTHONPATH": "/workspace",
                "PIP_CACHE_DIR": "/tmp/pip-cache",
                "DEBIAN_FRONTEND": "noninteractive",
                "USER": "devpocket",
                "HOME": "/home/devpocket",
            },
            "startup_commands": [
                "apt-get update",
                "apt-get install -y sudo curl wget git vim nano build-essential unzip tar gzip",
                "useradd -m -s /bin/bash devpocket",
                "echo 'devpocket:devpocket' | chpasswd",
                "usermod -aG sudo devpocket",
                "echo 'devpocket ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers",
                "mkdir -p /home/devpocket/workspace",
                "chown -R devpocket:devpocket /home/devpocket",
                "su - devpocket -c 'pip install --upgrade pip'",
                "su - devpocket -c 'pip install flask fastapi uvicorn jupyter pandas numpy requests virtualenv'",
            ],
            "documentation_url": "https://docs.python.org/3/",
            "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg",
        },
    ]

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
