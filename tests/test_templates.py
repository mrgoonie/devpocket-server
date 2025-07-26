"""Tests for template endpoints."""
import pytest
from httpx import AsyncClient

from app.models.template import TemplateCategory, TemplateStatus


@pytest.mark.asyncio
async def test_list_templates_unauthenticated(client: AsyncClient):
    """Test listing templates without authentication should fail."""
    response = await client.get("/api/v1/templates")
    assert response.status_code == 403


async def test_list_templates_authenticated(client: AsyncClient, authenticated_user):
    """Test listing templates with authentication."""
    response = await client.get(
        "/api/v1/templates", headers=authenticated_user["headers"]
    )
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)

    # Should have default templates
    assert len(data) >= 5

    # Check template structure
    for template in data:
        assert "id" in template
        assert "name" in template
        assert "display_name" in template
        assert "category" in template
        assert "docker_image" in template
        assert "status" in template


@pytest.mark.asyncio
async def test_list_templates_with_category_filter(
    client: AsyncClient, authenticated_user
):
    """Test listing templates with category filter."""
    response = await client.get(
        "/api/v1/templates",
        params={"category": "programming_language"},
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 200

    data = response.json()
    assert all(t["category"] == "programming_language" for t in data)


@pytest.mark.asyncio
async def test_list_templates_with_status_filter(
    client: AsyncClient, authenticated_user
):
    """Test listing templates with status filter."""
    response = await client.get(
        "/api/v1/templates",
        params={"status": "active"},
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 200

    data = response.json()
    assert all(t["status"] == "active" for t in data)


@pytest.mark.asyncio
async def test_get_template_by_id(client: AsyncClient, authenticated_user):
    """Test getting a specific template by ID."""
    # First list templates to get an ID
    list_response = await client.get(
        "/api/v1/templates", headers=authenticated_user["headers"]
    )
    templates = list_response.json()
    assert len(templates) > 0

    template_id = templates[0]["id"]

    # Get specific template
    response = await client.get(
        f"/api/v1/templates/{template_id}", headers=authenticated_user["headers"]
    )
    assert response.status_code == 200

    template = response.json()
    assert template["id"] == template_id
    assert "name" in template
    assert "docker_image" in template
    assert "default_resources" in template


@pytest.mark.asyncio
async def test_get_nonexistent_template(client: AsyncClient, authenticated_user):
    """Test getting a non-existent template."""
    fake_id = "507f1f77bcf86cd799439999"
    response = await client.get(
        f"/api/v1/templates/{fake_id}", headers=authenticated_user["headers"]
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_template_requires_admin(client: AsyncClient, authenticated_user):
    """Test that creating templates requires admin access."""
    template_data = {
        "name": "test-template",
        "display_name": "Test Template",
        "description": "A test template",
        "category": "programming_language",
        "tags": ["test"],
        "docker_image": "test:latest",
        "default_port": 8080,
        "default_resources": {"cpu": "500m", "memory": "1Gi", "storage": "10Gi"},
    }

    response = await client.post(
        "/api/v1/templates", json=template_data, headers=authenticated_user["headers"]
    )
    # Regular users should get 403 Forbidden
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_create_template(client: AsyncClient, admin_user):
    """Test that admin can create templates."""
    template_data = {
        "name": "ruby",
        "display_name": "Ruby 3.2",
        "description": "Ruby development environment",
        "category": "programming_language",
        "tags": ["ruby", "rails"],
        "docker_image": "ruby:3.2-slim",
        "default_port": 3000,
        "default_resources": {"cpu": "500m", "memory": "1Gi", "storage": "10Gi"},
        "environment_variables": {"RAILS_ENV": "development"},
        "startup_commands": ["gem install bundler"],
        "documentation_url": "https://www.ruby-lang.org/",
        "icon_url": "https://example.com/ruby.svg",
    }

    response = await client.post(
        "/api/v1/templates", json=template_data, headers=admin_user["headers"]
    )
    assert response.status_code == 201

    created = response.json()
    assert created["name"] == "ruby"
    assert created["display_name"] == "Ruby 3.2"
    assert created["status"] == "active"
    assert created["usage_count"] == 0


@pytest.mark.asyncio
async def test_create_duplicate_template_fails(client: AsyncClient, admin_user):
    """Test that creating duplicate template names fails."""
    # First create a template
    template_data = {
        "name": "python",
        "display_name": "Python 3.11",
        "description": "Original template",
        "category": "programming_language",
        "tags": ["python"],
        "docker_image": "python:3.11",
    }

    # Create the first template
    first_response = await client.post(
        "/api/v1/templates", json=template_data, headers=admin_user["headers"]
    )
    assert first_response.status_code == 201

    # Now try to create a duplicate - this should fail
    duplicate_data = {
        "name": "python",
        "display_name": "Python Duplicate",
        "description": "Duplicate template",
        "category": "programming_language",
        "tags": ["python"],
        "docker_image": "python:3.11",
    }

    response = await client.post(
        "/api/v1/templates", json=duplicate_data, headers=admin_user["headers"]
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_template_requires_admin(
    client: AsyncClient, authenticated_user, admin_user
):
    """Test that updating templates requires admin access."""
    # Get a template ID first
    list_response = await client.get(
        "/api/v1/templates", headers=authenticated_user["headers"]
    )
    templates = list_response.json()
    template_id = templates[0]["id"]

    update_data = {"description": "Updated description"}

    response = await client.put(
        f"/api/v1/templates/{template_id}",
        json=update_data,
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_update_template(client: AsyncClient, admin_user):
    """Test that admin can update templates."""
    # First create a template to update
    create_data = {
        "name": "nodejs-update-test",
        "display_name": "Node.js for Update Test",
        "description": "Original description",
        "category": "programming_language",
        "tags": ["nodejs", "original"],
        "docker_image": "node:18",
    }

    create_response = await client.post(
        "/api/v1/templates", json=create_data, headers=admin_user["headers"]
    )
    assert create_response.status_code == 201
    template_id = create_response.json()["id"]

    # Now update the template
    update_data = {
        "description": "Updated description for testing",
        "tags": ["updated", "test"],
    }

    response = await client.put(
        f"/api/v1/templates/{template_id}",
        json=update_data,
        headers=admin_user["headers"],
    )
    assert response.status_code == 200

    updated = response.json()
    assert updated["description"] == "Updated description for testing"
    assert "updated" in updated["tags"]
    assert "test" in updated["tags"]


@pytest.mark.asyncio
async def test_delete_template_requires_admin(
    client: AsyncClient, authenticated_user, admin_user
):
    """Test that deleting templates requires admin access."""
    # Get a template ID first
    list_response = await client.get(
        "/api/v1/templates", headers=authenticated_user["headers"]
    )
    templates = list_response.json()
    template_id = templates[0]["id"]

    response = await client.delete(
        f"/api/v1/templates/{template_id}", headers=authenticated_user["headers"]
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_delete_template(client: AsyncClient, admin_user):
    """Test that admin can delete (deprecate) templates."""
    # First create a template to delete
    create_data = {
        "name": "to-delete",
        "display_name": "To Delete",
        "description": "Template to be deleted",
        "category": "programming_language",
        "tags": ["test"],
        "docker_image": "test:latest",
    }

    create_response = await client.post(
        "/api/v1/templates", json=create_data, headers=admin_user["headers"]
    )
    assert create_response.status_code == 201
    template_id = create_response.json()["id"]

    # Delete the template
    response = await client.delete(
        f"/api/v1/templates/{template_id}", headers=admin_user["headers"]
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Template deleted successfully"

    # Verify it's deprecated (not visible to regular users)
    get_response = await client.get(
        f"/api/v1/templates/{template_id}", headers=admin_user["headers"]
    )
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "deprecated"


@pytest.mark.asyncio
async def test_initialize_templates_requires_admin(
    client: AsyncClient, authenticated_user
):
    """Test that initializing templates requires admin access."""
    response = await client.post(
        "/api/v1/templates/initialize", headers=authenticated_user["headers"]
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_initialize_templates(client: AsyncClient, admin_user):
    """Test that admin can initialize default templates."""
    response = await client.post(
        "/api/v1/templates/initialize", headers=admin_user["headers"]
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Default templates initialized successfully"

    # Verify default templates exist
    list_response = await client.get("/api/v1/templates", headers=admin_user["headers"])
    templates = list_response.json()
    template_names = [t["name"] for t in templates]

    # Check for default templates
    assert "python" in template_names
    assert "nodejs" in template_names
    assert "golang" in template_names
    assert "rust" in template_names
    assert "ubuntu" in template_names
