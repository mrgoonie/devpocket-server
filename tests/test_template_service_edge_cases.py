"""
Test template service edge cases and error scenarios.

This module tests the specific template service issues that were fixed:
1. Pydantic model serialization compatibility in template operations
2. Template creation and update edge cases
3. Template validation error handling
"""

from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId

from app.models.template import (
    TemplateCategory,
    TemplateCreate,
    TemplateInDB,
    TemplateStatus,
    TemplateUpdate,
)
from app.services.template_service import template_service


@pytest.mark.asyncio
class TestTemplateServicePydanticCompatibility:
    """Test template service Pydantic v1/v2 compatibility."""

    async def test_template_create_serialization_compatibility(self, test_database):
        """Test TemplateCreate serialization with both Pydantic versions."""
        template_service.set_database(test_database.database)

        template_data = TemplateCreate(
            name="test-template",
            display_name="Test Template",
            description="A test template",
            category=TemplateCategory.PROGRAMMING_LANGUAGE,
            docker_image="python:3.11",
            startup_commands=["echo 'hello'", "python --version"],
        )

        # Test dict method if available (Pydantic v1)
        if hasattr(template_data, "dict"):
            result = template_data.dict()
            assert isinstance(result, dict)
            assert result["name"] == "test-template"
            assert result["category"] == "programming_language"
            assert isinstance(result["startup_commands"], list)

        # Test model_dump method if available (Pydantic v2)
        if hasattr(template_data, "model_dump"):
            result = template_data.model_dump()
            assert isinstance(result, dict)
            assert result["name"] == "test-template"
            assert result["category"] == "programming_language"
            assert isinstance(result["startup_commands"], list)

    async def test_template_update_serialization_compatibility(self, test_database):
        """Test TemplateUpdate serialization with both Pydantic versions."""
        template_service.set_database(test_database.database)

        update_data = TemplateUpdate(
            display_name="Updated Template",
            description="Updated description",
            startup_commands=["echo 'updated'"],
        )

        # Test dict method if available (Pydantic v1)
        if hasattr(update_data, "dict"):
            result = update_data.dict()
            assert isinstance(result, dict)
            assert result["display_name"] == "Updated Template"
            assert (
                "name" not in result or result["name"] is None
            )  # Should exclude None values

        # Test model_dump method if available (Pydantic v2)
        if hasattr(update_data, "model_dump"):
            result = update_data.model_dump()
            assert isinstance(result, dict)
            assert result["display_name"] == "Updated Template"

    async def test_template_creation_with_pydantic_object(self, test_database):
        """Test template creation with actual Pydantic objects."""
        template_service.set_database(test_database.database)

        template_data = TemplateCreate(
            name="pydantic-test-template",
            display_name="Pydantic Test Template",
            description="Testing Pydantic serialization",
            category=TemplateCategory.PROGRAMMING_LANGUAGE,
            docker_image="python:3.11",
            startup_commands=["echo 'pydantic test'"],
        )

        # This should not raise serialization errors
        try:
            result = await template_service.create_template(template_data)
            assert result is not None
            assert result.name == "pydantic-test-template"
            assert isinstance(result, TemplateInDB)
        except Exception as e:
            # Should not fail due to serialization issues
            assert "dict" not in str(e).lower()
            assert "model_dump" not in str(e).lower()
            pytest.fail(f"Template creation failed with serialization error: {e}")

    async def test_template_update_with_pydantic_object(self, test_database):
        """Test template update with actual Pydantic objects."""
        template_service.set_database(test_database.database)

        # First create a template
        template_data = TemplateCreate(
            name="update-test-template",
            display_name="Update Test Template",
            description="Testing update serialization",
            category=TemplateCategory.PROGRAMMING_LANGUAGE,
            docker_image="python:3.11",
        )

        created_template = await template_service.create_template(template_data)

        # Now update it
        update_data = TemplateUpdate(
            display_name="Updated Test Template",
            description="Updated description for testing",
        )

        # This should not raise serialization errors
        try:
            result = await template_service.update_template(
                str(created_template.id), update_data
            )
            assert result is not None
            assert result.display_name == "Updated Test Template"
        except Exception as e:
            # Should not fail due to serialization issues
            assert "dict" not in str(e).lower()
            assert "model_dump" not in str(e).lower()
            pytest.fail(f"Template update failed with serialization error: {e}")

    async def test_template_serialization_compatibility_layer(self, test_database):
        """Test that template service handles both Pydantic v1 and v2 serialization methods."""
        template_service.set_database(test_database.database)

        # Create a real TemplateCreate object
        template_data = TemplateCreate(
            name="serialization-test",
            display_name="Serialization Test Template",
            description="Testing serialization compatibility",
            category=TemplateCategory.PROGRAMMING_LANGUAGE,
            docker_image="python:3.11",
            startup_commands=["echo 'test'"],
        )

        # Test that the template can be serialized using either method
        serialized_data = None
        if hasattr(template_data, "model_dump"):
            serialized_data = template_data.model_dump()
        elif hasattr(template_data, "dict"):
            serialized_data = template_data.dict()

        assert serialized_data is not None
        assert serialized_data["name"] == "serialization-test"
        assert serialized_data["category"] == "programming_language"

        # Test that the service can create the template
        result = await template_service.create_template(template_data)
        assert result is not None
        assert result.name == "serialization-test"


@pytest.mark.asyncio
class TestTemplateServiceEdgeCases:
    """Test template service edge cases and error scenarios."""

    async def test_template_creation_with_duplicate_name(self, test_database):
        """Test template creation with duplicate name."""
        template_service.set_database(test_database.database)

        template_data = TemplateCreate(
            name="duplicate-template",
            display_name="Duplicate Template",
            description="Testing duplicate names",
            category=TemplateCategory.PROGRAMMING_LANGUAGE,
            docker_image="python:3.11",
        )

        # Create first template
        await template_service.create_template(template_data)

        # Try to create second template with same name
        with pytest.raises(ValueError, match="already exists"):
            await template_service.create_template(template_data)

    async def test_template_creation_with_invalid_category(self, test_database):
        """Test template creation with invalid category."""
        template_service.set_database(test_database.database)

        # This should be caught by Pydantic validation before reaching the service
        with pytest.raises(ValueError):
            TemplateCreate(
                name="invalid-category-template",
                display_name="Invalid Category Template",
                description="Testing invalid category",
                category="invalid_category",  # Invalid category
                docker_image="python:3.11",
            )

    async def test_template_update_nonexistent_template(self, test_database):
        """Test updating a template that doesn't exist."""
        template_service.set_database(test_database.database)

        fake_id = str(ObjectId())
        update_data = TemplateUpdate(display_name="Updated Name")

        result = await template_service.update_template(fake_id, update_data)
        assert result is None

    async def test_template_update_with_invalid_object_id(self, test_database):
        """Test updating template with invalid ObjectId."""
        template_service.set_database(test_database.database)

        invalid_id = "invalid_object_id"
        update_data = TemplateUpdate(display_name="Updated Name")

        result = await template_service.update_template(invalid_id, update_data)
        assert result is None

    async def test_template_get_by_invalid_object_id(self, test_database):
        """Test getting template with invalid ObjectId."""
        template_service.set_database(test_database.database)

        invalid_id = "invalid_object_id"
        result = await template_service.get_template_by_id(invalid_id)
        assert result is None

    async def test_template_delete_nonexistent_template(self, test_database):
        """Test deleting a template that doesn't exist."""
        template_service.set_database(test_database.database)

        fake_id = str(ObjectId())
        result = await template_service.delete_template(fake_id)
        assert result is False

    async def test_template_delete_with_invalid_object_id(self, test_database):
        """Test deleting template with invalid ObjectId."""
        template_service.set_database(test_database.database)

        invalid_id = "invalid_object_id"
        result = await template_service.delete_template(invalid_id)
        assert result is False

    async def test_template_service_without_database(self):
        """Test template service operations without database initialization."""
        # Create new instance without database
        service = template_service.__class__()

        # Should raise ValueError for operations requiring database
        with pytest.raises(ValueError, match="Database not initialized"):
            await service.list_templates()

        with pytest.raises(ValueError, match="Database not initialized"):
            await service.get_template_by_id("some_id")

        with pytest.raises(ValueError, match="Database not initialized"):
            await service.get_template_by_name("some_name")

    async def test_template_creation_database_error(self, test_database):
        """Test template creation when database operation fails."""
        template_service.set_database(test_database.database)

        template_data = TemplateCreate(
            name="db-error-template",
            display_name="DB Error Template",
            description="Testing database errors",
            category=TemplateCategory.PROGRAMMING_LANGUAGE,
            docker_image="python:3.11",
        )

        # Mock database insert to fail
        with patch.object(
            test_database.database.templates,
            "insert_one",
            side_effect=Exception("Database error"),
        ):
            with pytest.raises(Exception, match="Database error"):
                await template_service.create_template(template_data)

    async def test_template_update_empty_data(self, test_database):
        """Test template update with empty update data."""
        template_service.set_database(test_database.database)

        # First create a template
        template_data = TemplateCreate(
            name="empty-update-template",
            display_name="Empty Update Template",
            description="Testing empty updates",
            category=TemplateCategory.PROGRAMMING_LANGUAGE,
            docker_image="python:3.11",
        )

        created_template = await template_service.create_template(template_data)

        # Update with empty data (all None values)
        update_data = TemplateUpdate()

        # Should return the existing template without changes
        result = await template_service.update_template(
            str(created_template.id), update_data
        )
        assert result is not None
        assert result.display_name == created_template.display_name

    async def test_template_list_with_filters(self, test_database):
        """Test template listing with category and status filters."""
        template_service.set_database(test_database.database)

        # Create templates with different categories and statuses
        template1 = TemplateCreate(
            name="filter-template-1",
            display_name="Filter Template 1",
            description="Programming language template",
            category=TemplateCategory.PROGRAMMING_LANGUAGE,
            docker_image="python:3.11",
        )

        template2 = TemplateCreate(
            name="filter-template-2",
            display_name="Filter Template 2",
            description="Operating system template",
            category=TemplateCategory.OPERATING_SYSTEM,
            docker_image="ubuntu:22.04",
        )

        await template_service.create_template(template1)
        created_template2 = await template_service.create_template(template2)

        # Update second template to deprecated status
        await template_service.update_template(
            str(created_template2.id), TemplateUpdate(status=TemplateStatus.DEPRECATED)
        )

        # Test filtering by category
        programming_templates = await template_service.list_templates(
            category=TemplateCategory.PROGRAMMING_LANGUAGE
        )
        assert len(programming_templates) >= 1
        assert any(t.name == "filter-template-1" for t in programming_templates)

        # Test filtering by status
        active_templates = await template_service.list_templates(
            status=TemplateStatus.ACTIVE
        )
        deprecated_templates = await template_service.list_templates(
            status=TemplateStatus.DEPRECATED
        )

        # Should have different counts
        assert len(active_templates) != len(deprecated_templates)


@pytest.mark.asyncio
class TestTemplateValidationEdgeCases:
    """Test template validation edge cases."""

    async def test_template_package_validation_with_malformed_commands(
        self, test_database
    ):
        """Test template package validation with malformed startup commands."""
        template_service.set_database(test_database.database)

        # Test with non-string commands
        template_data = {
            "name": "malformed-commands-template",
            "startup_commands": [
                "echo 'valid command'",
                123,  # Invalid: number instead of string
                {"command": "echo 'dict command'"},  # Invalid: dict instead of string
                None,  # Invalid: None value
                ["nested", "list"],  # Invalid: nested list
            ],
        }

        # Should handle malformed commands gracefully
        try:
            validation_result = await template_service.validate_template_packages(
                template_data
            )
            assert isinstance(validation_result, dict)
            assert "warnings" in validation_result
            assert "errors" in validation_result
            # Should have warnings about non-string commands
            assert len(validation_result["warnings"]) > 0
        except Exception as e:
            pytest.fail(
                f"Package validation should handle malformed commands gracefully: {e}"
            )

    async def test_template_package_validation_with_empty_commands(self, test_database):
        """Test template package validation with empty startup commands."""
        template_service.set_database(test_database.database)

        template_data = {"name": "empty-commands-template", "startup_commands": []}

        # Should handle empty commands gracefully
        validation_result = await template_service.validate_template_packages(
            template_data
        )
        assert isinstance(validation_result, dict)
        assert validation_result["valid"] is True  # No packages to validate
        assert len(validation_result["validated_packages"]) == 0

    async def test_template_package_validation_with_missing_commands(
        self, test_database
    ):
        """Test template package validation with missing startup_commands field."""
        template_service.set_database(test_database.database)

        template_data = {
            "name": "missing-commands-template"
            # Missing startup_commands field
        }

        # Should handle missing commands gracefully
        validation_result = await template_service.validate_template_packages(
            template_data
        )
        assert isinstance(validation_result, dict)
        assert validation_result["valid"] is True  # No packages to validate

    async def test_template_package_validation_network_error(self, test_database):
        """Test template package validation with network errors."""
        template_service.set_database(test_database.database)

        template_data = {
            "name": "network-error-template",
            "startup_commands": ["npm install express", "pip install flask"],
        }

        # Mock httpx to raise network error
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = (
                Exception("Network error")
            )

            validation_result = await template_service.validate_template_packages(
                template_data
            )
            assert isinstance(validation_result, dict)
            # Should have warnings about network errors
            assert len(validation_result["warnings"]) > 0

    async def test_template_increment_usage_count_invalid_id(self, test_database):
        """Test incrementing usage count with invalid template ID."""
        template_service.set_database(test_database.database)

        # Should not raise exception for invalid ID
        try:
            await template_service.increment_usage_count("invalid_id")
        except Exception as e:
            pytest.fail(
                f"increment_usage_count should handle invalid IDs gracefully: {e}"
            )

    async def test_template_create_from_data_with_invalid_data(self, test_database):
        """Test creating template from invalid data dictionary."""
        template_service.set_database(test_database.database)

        invalid_data = {
            "name": "invalid-data-template",
            # Missing required fields like display_name, description, etc.
            "invalid_field": "invalid_value",
        }

        # Should raise appropriate error for missing required fields
        with pytest.raises(Exception):
            await template_service.create_template_from_data(invalid_data)
