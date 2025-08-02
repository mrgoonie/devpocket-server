#!/usr/bin/env python3
"""
Test script to investigate MongoDB serialization issues with environment_variables
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import json
from datetime import datetime, timezone

from bson import ObjectId

from app.models.environment import (
    EnvironmentCreate,
    EnvironmentInDB,
    EnvironmentTemplate,
)
from app.models.template import TemplateInDB


def test_environment_serialization():
    """Test how environment models serialize environment_variables"""

    print("=== Testing Environment Serialization ===")

    # Test 1: Environment creation model
    env_create = EnvironmentCreate(
        name="test-env",
        template=EnvironmentTemplate.PYTHON,
        environment_variables={"PYTHON_PATH": "/workspace", "DEBUG": "true"},
    )

    print("1. EnvironmentCreate model:")
    print(f"   Type of environment_variables: {type(env_create.environment_variables)}")
    print(f"   Value: {env_create.environment_variables}")
    print(f"   model_dump(): {env_create.model_dump()}")
    print()

    # Test 2: Environment database model
    env_db = EnvironmentInDB(
        _id=ObjectId(),
        user_id=ObjectId(),
        name="test-env",
        template=EnvironmentTemplate.PYTHON,
        resources={"cpu": "500m", "memory": "1Gi", "storage": "10Gi"},
        environment_variables={"PYTHON_PATH": "/workspace", "DEBUG": "true"},
    )

    print("2. EnvironmentInDB model:")
    print(f"   Type of environment_variables: {type(env_db.environment_variables)}")
    print(f"   Value: {env_db.environment_variables}")

    # Test serialization
    db_dict = env_db.model_dump(by_alias=True)
    print(f"   model_dump(by_alias=True): {type(db_dict['environment_variables'])}")
    print(f"   environment_variables in dict: {db_dict['environment_variables']}")
    print()

    # Test 3: JSON serialization
    try:
        json_str = json.dumps(db_dict, default=str)
        print("3. JSON serialization:")
        print(f"   Success: {json_str[:200]}...")

        # Test deserialization
        parsed_back = json.loads(json_str)
        print(
            f"   After JSON round-trip, environment_variables type: {type(parsed_back['environment_variables'])}"
        )
        print(f"   Value: {parsed_back['environment_variables']}")
    except Exception as e:
        print(f"   JSON serialization failed: {e}")
    print()

    # Test 4: Simulating what happens when data comes from MongoDB
    print("4. Simulating MongoDB data retrieval:")

    # This simulates what we might get from MongoDB if serialization is wrong
    malformed_data = {
        "_id": ObjectId(),
        "user_id": ObjectId(),
        "name": "test-env",
        "template": "python",
        "status": "creating",
        "resources": {"cpu": "500m", "memory": "1Gi", "storage": "10Gi"},
        "environment_variables": '{"PYTHON_PATH": "/workspace", "DEBUG": "true"}',  # String instead of dict
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    print(
        f"   Malformed data environment_variables type: {type(malformed_data['environment_variables'])}"
    )

    try:
        # This would fail if environment_variables is a string but model expects Dict[str, str]
        env_from_db = EnvironmentInDB(**malformed_data)
        print(
            f"   Successfully created model from malformed data: {env_from_db.environment_variables}"
        )
    except Exception as e:
        print(f"   Failed to create model from malformed data: {e}")
    print()

    # Test 5: Template model
    template = TemplateInDB(
        _id=ObjectId(),
        name="python",
        display_name="Python 3.11",
        description="Python environment",
        category="programming_language",
        docker_image="python:3.11-slim",
        environment_variables={
            "PYTHON_PATH": "/workspace",
            "PIP_CACHE_DIR": "/tmp/pip-cache",
        },
        created_by=ObjectId(),
    )

    print("5. TemplateInDB model:")
    print(f"   Type of environment_variables: {type(template.environment_variables)}")
    template_dict = template.model_dump(by_alias=True)
    print(
        f"   After model_dump, environment_variables type: {type(template_dict['environment_variables'])}"
    )
    print(f"   Value: {template_dict['environment_variables']}")


if __name__ == "__main__":
    test_environment_serialization()
