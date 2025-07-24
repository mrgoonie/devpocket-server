#!/usr/bin/env python3
"""
Simple test to validate template data structures without dependencies.
"""

import sys
import os
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum

# Recreate the essential models locally to test validation
class TemplateCategory(str, Enum):
    PROGRAMMING_LANGUAGE = "programming_language"
    FRAMEWORK = "framework"
    DATABASE = "database"
    DEVOPS = "devops"
    OPERATING_SYSTEM = "operating_system"

class TemplateStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    BETA = "beta"

# Sample template data similar to what's in the database
sample_templates = [
    {
        "_id": "673ec60a6cc28a9f0dd6efa1",
        "name": "python",
        "display_name": "Python 3.11",
        "description": "Python development environment with pip, virtualenv, and common packages pre-installed. Includes VS Code Server for web-based development.",
        "category": "programming_language",
        "tags": ["python", "python3", "pip", "virtualenv", "flask", "django"],
        "docker_image": "python:3.11-slim",
        "default_port": 8080,
        "default_resources": {
            "cpu": "500m",
            "memory": "1Gi",
            "storage": "10Gi"
        },
        "environment_variables": {
            "PYTHONPATH": "/workspace",
            "PIP_CACHE_DIR": "/tmp/pip-cache"
        },
        "startup_commands": [
            "pip install --upgrade pip",
            "pip install flask fastapi uvicorn jupyter",
            "mkdir -p /workspace"
        ],
        "documentation_url": "https://docs.python.org/3/",
        "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg",
        "status": "active",
        "version": "1.0.0",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "created_by": "system",
        "usage_count": 0
    },
    {
        "_id": "673ec60a6cc28a9f0dd6efa2",
        "name": "nodejs",
        "display_name": "Node.js 18 LTS",
        "description": "Node.js development environment with npm, yarn, and popular packages. Perfect for building web applications, APIs, and microservices.",
        "category": "programming_language",
        "tags": ["nodejs", "npm", "yarn", "express", "react", "vue", "javascript"],
        "docker_image": "node:18-slim",
        "default_port": 3000,
        "default_resources": {
            "cpu": "500m",
            "memory": "1Gi",
            "storage": "10Gi"
        },
        "environment_variables": {
            "NODE_ENV": "development",
            "npm_config_cache": "/tmp/npm-cache"
        },
        "startup_commands": [
            "npm install -g nodemon typescript @types/node",
            "mkdir -p /workspace",
            "cd /workspace"
        ],
        "documentation_url": "https://nodejs.org/en/docs/",
        "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/nodejs/nodejs-original.svg",
        "status": "active",
        "version": "1.0.0",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "created_by": "system",
        "usage_count": 0
    }
]

def test_template_conversion():
    """Test converting template data to the expected response format"""
    print("Testing template data conversion...")
    
    successful_conversions = 0
    
    for i, template_data in enumerate(sample_templates, 1):
        print(f"\n--- Testing Template {i}: {template_data.get('name', 'unknown')} ---")
        
        try:
            # Simulate the same conversion logic as in the service
            template_dict = dict(template_data)
            template_dict["id"] = str(template_dict.pop("_id"))
            
            # Check required fields for TemplateResponse
            required_fields = ['id', 'name', 'display_name', 'description', 
                             'category', 'tags', 'docker_image', 'default_port',
                             'default_resources', 'environment_variables', 
                             'startup_commands', 'documentation_url', 'icon_url',
                             'status', 'version', 'created_at', 'updated_at', 'usage_count']
            
            missing_fields = []
            for field in required_fields:
                if field not in template_dict:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"❌ Missing fields: {missing_fields}")
            else:
                print(f"✅ All required fields present")
                
            # Check data types
            print(f"   ID: {template_dict['id']} (type: {type(template_dict['id'])})")
            print(f"   Category: {template_dict['category']} (type: {type(template_dict['category'])})")
            print(f"   Status: {template_dict['status']} (type: {type(template_dict['status'])})")
            print(f"   Tags: {len(template_dict.get('tags', []))} items")
            print(f"   Resources: {template_dict.get('default_resources', {}).keys()}")
            
            # Validate enum values
            if template_dict['category'] not in [e.value for e in TemplateCategory]:
                print(f"❌ Invalid category: {template_dict['category']}")
            else:
                print(f"✅ Valid category")
                
            if template_dict['status'] not in [e.value for e in TemplateStatus]:
                print(f"❌ Invalid status: {template_dict['status']}")
            else:
                print(f"✅ Valid status")
            
            successful_conversions += 1
            print(f"✅ Template conversion successful")
            
        except Exception as e:
            print(f"❌ Template conversion failed: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n=== Summary ===")
    print(f"Successfully converted: {successful_conversions}/{len(sample_templates)} templates")
    
    if successful_conversions == len(sample_templates):
        print("✅ All templates should convert successfully")
        print("The issue might be with:")
        print("  - Database connection")
        print("  - Actual data in database differs from expected")
        print("  - Error in the API filtering logic")
    else:
        print("❌ Some templates have data issues")

if __name__ == "__main__":
    test_template_conversion()