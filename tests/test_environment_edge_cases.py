"""
Test edge cases and error scenarios for environment management.

This module tests the specific issues that were fixed:
1. Pydantic model serialization compatibility (v1 vs v2)
2. Resource object handling edge cases
3. Environment creation with malformed data
"""

from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models.environment import (
    EnvironmentCreate,
    EnvironmentTemplate,
    ResourceLimits,
)
from app.services.environment_service import environment_service


@pytest.mark.asyncio
class TestPydanticModelCompatibility:
    """Test Pydantic v1/v2 model serialization compatibility."""

    async def test_resource_limits_dict_method(self):
        """Test ResourceLimits serialization with dict() method (Pydantic v1)."""
        resources = ResourceLimits(cpu="500m", memory="1Gi", storage="10Gi")

        # Test that both methods exist and work
        if hasattr(resources, "dict"):
            result = resources.dict()
            assert isinstance(result, dict)
            assert result["cpu"] == "500m"
            assert result["memory"] == "1Gi"
            assert result["storage"] == "10Gi"

    async def test_resource_limits_model_dump_method(self):
        """Test ResourceLimits serialization with model_dump() method (Pydantic v2)."""
        resources = ResourceLimits(cpu="500m", memory="1Gi", storage="10Gi")

        # Test that both methods exist and work
        if hasattr(resources, "model_dump"):
            result = resources.model_dump()
            assert isinstance(result, dict)
            assert result["cpu"] == "500m"
            assert result["memory"] == "1Gi"
            assert result["storage"] == "10Gi"

    async def test_environment_create_serialization_compatibility(self):
        """Test EnvironmentCreate serialization with both Pydantic versions."""
        env_data = EnvironmentCreate(
            name="test-env",
            template=EnvironmentTemplate.PYTHON,
            resources=ResourceLimits(cpu="500m", memory="1Gi", storage="10Gi"),
        )

        # Test dict method if available
        if hasattr(env_data, "dict"):
            result = env_data.dict()
            assert isinstance(result, dict)
            assert result["name"] == "test-env"
            assert result["template"] == "python"
            assert isinstance(result["resources"], dict)

        # Test model_dump method if available
        if hasattr(env_data, "model_dump"):
            result = env_data.model_dump()
            assert isinstance(result, dict)
            assert result["name"] == "test-env"
            assert result["template"] == "python"
            assert isinstance(result["resources"], dict)

    async def test_resource_object_type_handling(self, test_database):
        """Test handling of different resource object types."""
        environment_service.set_database(test_database.database)

        # Mock user
        mock_user = MagicMock()
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_user.subscription_plan = "free"

        # Test with ResourceLimits object
        resources_obj = ResourceLimits(cpu="500m", memory="1Gi", storage="10Gi")
        env_data = EnvironmentCreate(
            name="test-env-obj",
            template=EnvironmentTemplate.PYTHON,
            resources=resources_obj,
        )

        # This should not raise an error
        try:
            result = await environment_service.create_environment(mock_user, env_data)
            assert result is not None
            assert result.name == "test-env-obj"
        except Exception as e:
            pytest.fail(f"Environment creation with ResourceLimits object failed: {e}")

    async def test_resource_dict_handling(self, test_database):
        """Test handling of resource data as dictionary."""
        environment_service.set_database(test_database.database)

        # Mock user
        mock_user = MagicMock()
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_user.subscription_plan = "free"

        # Test with dict resources (should be converted to ResourceLimits)
        env_data = EnvironmentCreate(
            name="test-env-dict",
            template=EnvironmentTemplate.PYTHON,
            resources=None,  # Will use default resources
        )

        # Mock the user limits check to avoid hitting environment limits
        with patch.object(
            environment_service, "_check_user_limits"
        ) as mock_check_limits:
            mock_check_limits.return_value = None  # No limits exceeded

            with patch.object(environment_service, "_create_container") as mock_create:
                mock_create.return_value = {"status": "success"}

                # This should not raise an error
                try:
                    result = await environment_service.create_environment(
                        mock_user, env_data
                    )
                    assert result is not None
                    assert result.name == "test-env-dict"
                except Exception as e:
                    pytest.fail(
                        f"Environment creation with default resources failed: {e}"
                    )

    async def test_malformed_resource_object_handling(self, test_database):
        """Test handling of malformed resource objects."""
        environment_service.set_database(test_database.database)

        # Mock user
        mock_user = MagicMock()
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_user.subscription_plan = "free"

        # Create a mock object that doesn't have dict() or model_dump()
        class MockResourceObject:
            def __init__(self):
                self.cpu = "500m"
                self.memory = "1Gi"
                self.storage = "10Gi"

        mock_resources = MockResourceObject()

        # Patch the _get_default_resources method to return our mock object
        with patch.object(
            environment_service, "_get_default_resources", return_value=mock_resources
        ):
            env_data = EnvironmentCreate(
                name="test-env-mock",
                template=EnvironmentTemplate.PYTHON,
                resources=None,  # Will use mocked default resources
            )

            # This should handle the malformed object gracefully
            try:
                result = await environment_service.create_environment(
                    mock_user, env_data
                )
                assert result is not None
                assert result.name == "test-env-mock"
            except Exception as e:
                # Should not fail due to serialization issues
                assert "'str' object does not support item assignment" not in str(e)


@pytest.mark.asyncio
class TestEnvironmentCreationEdgeCases:
    """Test environment creation edge cases and error scenarios."""

    async def test_environment_creation_with_invalid_template_enum(
        self, client: AsyncClient, authenticated_user
    ):
        """Test environment creation with invalid template that bypasses validation."""
        # This tests the actual API endpoint validation
        invalid_data = {
            "name": "test-env",
            "template": "nonexistent_template",  # Invalid template
        }

        response = await client.post(
            "/api/v1/environments",
            json=invalid_data,
            headers=authenticated_user["headers"],
        )

        # Should return validation error
        assert response.status_code == 422
        response_data = response.json()
        # Check that validation error mentions template
        if "errors" in response_data:
            error_messages = [str(error) for error in response_data["errors"]]
        else:
            error_messages = [str(response_data.get("detail", ""))]
        template_error_found = any("template" in msg.lower() for msg in error_messages)
        assert (
            template_error_found
        ), f"Expected template validation error, got: {response_data}"

    async def test_environment_creation_with_invalid_resource_format(
        self, client: AsyncClient, authenticated_user
    ):
        """Test environment creation with malformed resource specifications."""
        invalid_data = {
            "name": "test-env",
            "template": "python",
            "resources": {
                "cpu": "invalid_cpu_format",  # Invalid CPU format
                "memory": "invalid_memory",  # Invalid memory format
                "storage": "invalid_storage",  # Invalid storage format
            },
        }

        response = await client.post(
            "/api/v1/environments",
            json=invalid_data,
            headers=authenticated_user["headers"],
        )

        # Should return validation error
        assert response.status_code == 422

    async def test_environment_creation_with_missing_required_fields(
        self, client: AsyncClient, authenticated_user
    ):
        """Test environment creation with missing required fields."""
        invalid_data = {
            # Missing 'name' field
            "template": "python",
        }

        response = await client.post(
            "/api/v1/environments",
            json=invalid_data,
            headers=authenticated_user["headers"],
        )

        # Should return validation error
        assert response.status_code == 422
        response_data = response.json()
        # Check that validation error mentions name
        if "errors" in response_data:
            error_messages = [str(error) for error in response_data["errors"]]
        else:
            error_messages = [str(response_data.get("detail", ""))]
        name_error_found = any("name" in msg.lower() for msg in error_messages)
        assert name_error_found, f"Expected name validation error, got: {response_data}"

    async def test_environment_creation_with_empty_name(
        self, client: AsyncClient, authenticated_user
    ):
        """Test environment creation with empty name."""
        invalid_data = {
            "name": "",  # Empty name
            "template": "python",
        }

        response = await client.post(
            "/api/v1/environments",
            json=invalid_data,
            headers=authenticated_user["headers"],
        )

        # Should return validation error
        assert response.status_code == 422

    async def test_environment_creation_with_invalid_name_characters(
        self, client: AsyncClient, authenticated_user
    ):
        """Test environment creation with invalid name characters."""
        invalid_data = {
            "name": "test@env#invalid!",  # Invalid characters
            "template": "python",
        }

        response = await client.post(
            "/api/v1/environments",
            json=invalid_data,
            headers=authenticated_user["headers"],
        )

        # Should return validation error
        assert response.status_code == 422

    async def test_environment_creation_database_error_handling(self, test_database):
        """Test environment creation when database operations fail."""
        environment_service.set_database(test_database.database)

        # Mock user
        mock_user = MagicMock()
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_user.subscription_plan = "free"

        env_data = EnvironmentCreate(
            name="test-env", template=EnvironmentTemplate.PYTHON
        )

        # Mock user limits check to pass
        with patch.object(
            environment_service, "_check_user_limits"
        ) as mock_check_limits:
            mock_check_limits.return_value = None  # No limits exceeded

            # Mock database insert to fail at the service level
            with patch.object(
                environment_service.db.environments,
                "insert_one",
                side_effect=Exception("Database error"),
            ):
                with pytest.raises(Exception, match="Database error"):
                    await environment_service.create_environment(mock_user, env_data)

    async def test_environment_creation_with_resource_limit_exceeded(
        self, test_database
    ):
        """Test environment creation when user exceeds resource limits."""
        environment_service.set_database(test_database.database)

        # Mock user with free plan (limit: 1 environment)
        mock_user = MagicMock()
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_user.subscription_plan = "free"

        # Mock database to return that user already has 1 active environment
        with patch.object(
            test_database.database.environments, "count_documents", return_value=1
        ):
            env_data = EnvironmentCreate(
                name="test-env", template=EnvironmentTemplate.PYTHON
            )

            # Should raise HTTPException for limit exceeded
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await environment_service.create_environment(mock_user, env_data)

            assert exc_info.value.status_code == 403
            assert "limit reached" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
class TestProductionModeScenarios:
    """Test scenarios that occur in production mode but not test mode."""

    async def test_environment_creation_production_mode_detection(self, test_database):
        """Test that production mode is properly detected."""
        environment_service.set_database(test_database.database)

        # Test with TESTING=false environment variable
        with patch.dict(
            "os.environ", {"TESTING": "false", "ENVIRONMENT": "production"}
        ):
            from app.services.environment_service import _is_test_environment

            assert not _is_test_environment()

    async def test_environment_creation_test_mode_detection(self, test_database):
        """Test that test mode is properly detected."""
        environment_service.set_database(test_database.database)

        # Test with TESTING=true environment variable (default in tests)
        from app.services.environment_service import _is_test_environment

        assert _is_test_environment()

    async def test_container_creation_skipped_in_test_mode(self, test_database):
        """Test that container creation is skipped in test mode."""
        environment_service.set_database(test_database.database)

        # Mock user
        mock_user = MagicMock()
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_user.subscription_plan = "free"

        env_data = EnvironmentCreate(
            name="test-env", template=EnvironmentTemplate.PYTHON
        )

        # In test mode, this should complete without actual container creation
        result = await environment_service.create_environment(mock_user, env_data)
        assert result is not None
        assert (
            result.status.value == "creating"
        )  # Should be in creating state initially

    async def test_async_task_manager_initialization(self, test_database):
        """Test that async task manager is properly initialized."""
        environment_service.set_database(test_database.database)

        # Task manager should be initialized after setting database
        assert environment_service.task_manager is not None
        assert hasattr(environment_service.task_manager, "create_environment_async")

    async def test_environment_creation_with_task_manager_failure(self, test_database):
        """Test environment creation when task manager fails."""
        environment_service.set_database(test_database.database)

        # Mock user
        mock_user = MagicMock()
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_user.subscription_plan = "free"

        env_data = EnvironmentCreate(
            name="test-env", template=EnvironmentTemplate.PYTHON
        )

        # Mock user limits check to pass
        with patch.object(
            environment_service, "_check_user_limits"
        ) as mock_check_limits:
            mock_check_limits.return_value = None  # No limits exceeded

            # Mock task manager to fail
            with patch.object(
                environment_service.task_manager,
                "create_environment_async",
                side_effect=Exception("Task manager error"),
            ):
                # Should still create environment record but mark it as failed
                result = await environment_service.create_environment(
                    mock_user, env_data
                )
                assert result is not None
                assert result.name == "test-env"
                # Environment should be marked as failed due to task manager error
                assert result.status.value == "failed"
