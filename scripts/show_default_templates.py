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
            "name": "python",
            "display_name": "Python 3.11",
            "description": "Python development environment with pip, virtualenv, and common packages pre-installed. Includes VS Code Server for web-based development.",
            "category": "programming_language",
            "tags": ["python", "python3", "pip", "virtualenv", "flask", "django"],
            "docker_image": "python:3.11-slim",
            "default_port": 8080,
            "default_resources": {"cpu": "500m", "memory": "1Gi", "storage": "10Gi"},
            "environment_variables": {
                "PYTHONPATH": "/workspace",
                "PIP_CACHE_DIR": "/tmp/pip-cache",
            },
            "startup_commands": [
                "pip install --upgrade pip",
                "pip install flask fastapi uvicorn jupyter",
                "mkdir -p /workspace",
            ],
            "documentation_url": "https://docs.python.org/3/",
            "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg",
        },
        {
            "name": "nodejs",
            "display_name": "Node.js 18 LTS",
            "description": "Node.js development environment with npm, yarn, and popular packages. Perfect for building web applications, APIs, and microservices.",
            "category": "programming_language",
            "tags": ["nodejs", "npm", "yarn", "express", "react", "vue", "javascript"],
            "docker_image": "node:18-slim",
            "default_port": 3000,
            "default_resources": {"cpu": "500m", "memory": "1Gi", "storage": "10Gi"},
            "environment_variables": {
                "NODE_ENV": "development",
                "npm_config_cache": "/tmp/npm-cache",
            },
            "startup_commands": [
                "npm install -g nodemon typescript @types/node",
                "mkdir -p /workspace",
                "cd /workspace",
            ],
            "documentation_url": "https://nodejs.org/en/docs/",
            "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/nodejs/nodejs-original.svg",
        },
        {
            "name": "golang",
            "display_name": "Go 1.21",
            "description": "Go development environment with the latest Go compiler and common tools. Ideal for building fast, reliable, and efficient software.",
            "category": "programming_language",
            "tags": ["go", "golang", "gin", "fiber", "gorilla"],
            "docker_image": "golang:1.21-alpine",
            "default_port": 8080,
            "default_resources": {"cpu": "500m", "memory": "1Gi", "storage": "10Gi"},
            "environment_variables": {
                "GOPATH": "/go",
                "GOROOT": "/usr/local/go",
                "PATH": "/usr/local/go/bin:/go/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            },
            "startup_commands": [
                "go install github.com/air-verse/air@latest",
                "go install github.com/cosmtrek/air@latest",
                "mkdir -p /workspace",
            ],
            "documentation_url": "https://golang.org/doc/",
            "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/go/go-original.svg",
        },
        {
            "name": "rust",
            "display_name": "Rust Latest",
            "description": "Rust development environment with rustc, cargo, and essential tools. Build fast and memory-safe applications.",
            "category": "programming_language",
            "tags": ["rust", "cargo", "rustc", "actix", "tokio"],
            "docker_image": "rust:latest",
            "default_port": 8080,
            "default_resources": {"cpu": "1000m", "memory": "2Gi", "storage": "15Gi"},
            "environment_variables": {
                "CARGO_HOME": "/usr/local/cargo",
                "RUSTUP_HOME": "/usr/local/rustup",
            },
            "startup_commands": [
                "rustup update",
                "cargo install cargo-watch",
                "mkdir -p /workspace",
            ],
            "documentation_url": "https://doc.rust-lang.org/",
            "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/rust/rust-plain.svg",
        },
        {
            "name": "ubuntu",
            "display_name": "Ubuntu 22.04 LTS",
            "description": "Clean Ubuntu environment with essential development tools. Perfect for custom setups and system administration tasks.",
            "category": "operating_system",
            "tags": ["ubuntu", "linux", "bash", "shell", "development"],
            "docker_image": "ubuntu:22.04",
            "default_port": 8080,
            "default_resources": {"cpu": "500m", "memory": "1Gi", "storage": "10Gi"},
            "environment_variables": {
                "DEBIAN_FRONTEND": "noninteractive",
                "TERM": "xterm-256color",
            },
            "startup_commands": [
                "apt-get update",
                "apt-get install -y curl wget git vim nano build-essential",
                "mkdir -p /workspace",
            ],
            "documentation_url": "https://ubuntu.com/server/docs",
            "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/ubuntu/ubuntu-plain.svg",
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
