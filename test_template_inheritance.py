#!/usr/bin/env python3
"""
Test script to check how environment_variables are inherited from templates
"""

import asyncio
import os
import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import json

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.models.environment import EnvironmentCreate, EnvironmentTemplate
from app.models.user import UserInDB
from app.services.environment_service import environment_service
from app.services.template_service import template_service


async def test_template_inheritance():
    """Test how environment_variables are inherited from templates"""

    print("=== Testing Template Environment Variables Inheritance ===")

    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    # Set database for services
    template_service.set_database(db)
    environment_service.set_database(db)

    try:
        # Test 1: Check if templates exist and their environment_variables
        print("1. Checking template data in database:")
        python_template = await template_service.get_template_by_name("python")
        if python_template:
            print(f"   Python template found: {python_template.name}")
            print(
                f"   Template environment_variables type: {type(python_template.environment_variables)}"
            )
            print(
                f"   Template environment_variables: {python_template.environment_variables}"
            )
        else:
            print("   Python template not found in database")
        print()

        # Test 2: Check how environment creation handles template data
        print("2. Testing environment creation without template merge:")

        # Create a mock user
        mock_user = UserInDB(
            _id=ObjectId(),
            username="testuser",
            email="test@example.com",
            hashed_password="dummy",
            subscription_plan="free",
        )

        # Create environment data - note: no environment_variables provided by user
        env_create = EnvironmentCreate(
            name="test-env",
            template=EnvironmentTemplate.PYTHON,
            # environment_variables not provided - should inherit from template
        )

        print(f"   User environment_variables: {env_create.environment_variables}")
        print(
            f"   Template environment_variables: {python_template.environment_variables if python_template else 'N/A'}"
        )

        # Test current environment creation logic
        print("   Current logic result:")
        merged_env_vars = env_create.environment_variables or {}
        print(f"   Final environment_variables: {merged_env_vars}")
        print(f"   Type: {type(merged_env_vars)}")
        print()

        # Test 3: What SHOULD happen - merge template and user variables
        print("3. What should happen (proper template inheritance):")
        if python_template:
            # This is what should happen - merge template vars with user vars
            template_vars = python_template.environment_variables or {}
            user_vars = env_create.environment_variables or {}
            merged_vars = {
                **template_vars,
                **user_vars,
            }  # User vars override template vars

            print(f"   Template vars: {template_vars}")
            print(f"   User vars: {user_vars}")
            print(f"   Properly merged vars: {merged_vars}")
            print(f"   Type: {type(merged_vars)}")
        print()

        # Test 4: Check how template data is serialized in database
        print("4. Checking how template is stored in MongoDB:")
        raw_template = await db.templates.find_one({"name": "python"})
        if raw_template:
            print(
                f"   Raw MongoDB environment_variables type: {type(raw_template.get('environment_variables'))}"
            )
            print(
                f"   Raw MongoDB environment_variables: {raw_template.get('environment_variables')}"
            )

            # Check if it's a string (which would be wrong)
            if isinstance(raw_template.get("environment_variables"), str):
                print("   ❌ ERROR: environment_variables stored as string in MongoDB!")
                try:
                    parsed = json.loads(raw_template["environment_variables"])
                    print(f"   Parsed from JSON string: {parsed}")
                except Exception as e:
                    print(f"   Failed to parse JSON: {e}")
            else:
                print("   ✅ GOOD: environment_variables stored as proper BSON object")
        print()

    except Exception as e:
        print(f"Error during test: {e}")
        import traceback

        traceback.print_exc()
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(test_template_inheritance())
