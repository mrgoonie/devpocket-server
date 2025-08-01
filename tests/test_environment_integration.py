"""
Integration tests for environment creation with Kubernetes

These tests create actual Kubernetes resources and validate the full environment
creation workflow including tmux session management and ConfigMap-based initialization.
"""

import asyncio
import base64
import os
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import pytest
import pytest_asyncio
import yaml
from bson import ObjectId
from kubernetes import client, config as k8s_config
from kubernetes.client.exceptions import ApiException
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.models.cluster import ClusterInDB, ClusterRegion, ClusterStatus
from app.models.environment import (
    EnvironmentInDB,
    EnvironmentStatus,
    EnvironmentTemplate,
    ResourceLimits,
)
from app.services.cluster_service import cluster_service
from app.services.environment_service import environment_service
from app.services.template_service import template_service
from app.services.tmux_service import tmux_manager


class KubernetesTestManager:
    """Manages Kubernetes resources for integration tests"""

    def __init__(self):
        self.created_resources = []
        self.test_namespace = f"devpocket-test-{uuid.uuid4().hex[:8]}"
        self.v1_core = None
        self.v1_apps = None

    async def setup_kubernetes_client(self):
        """Setup Kubernetes client using OVH kubeconfig"""
        try:
            # Try to load OVH kubeconfig first
            ovh_kubeconfig = (
                Path(__file__).parent.parent / "k8s" / "kube_config_ovh.yaml"
            )
            if ovh_kubeconfig.exists():
                k8s_config.load_kube_config(config_file=str(ovh_kubeconfig))
                print(f"Loaded OVH kubeconfig from {ovh_kubeconfig}")
            else:
                # Fallback to default kubeconfig
                k8s_config.load_kube_config()
                print("Loaded default kubeconfig")

            # Disable SSL verification for testing (OVH cluster has certificate issues)
            configuration = client.Configuration.get_default_copy()
            configuration.verify_ssl = False
            configuration.ssl_ca_cert = None
            from urllib3 import disable_warnings
            from urllib3.exceptions import InsecureRequestWarning

            disable_warnings(InsecureRequestWarning)

            self.v1_core = client.CoreV1Api(client.ApiClient(configuration))
            self.v1_apps = client.AppsV1Api(client.ApiClient(configuration))

            # Test connectivity with a simple API call
            try:
                # Try to list namespaces with a reasonable timeout
                self.v1_core.list_namespace(_request_timeout=10)
                print("Successfully connected to Kubernetes cluster")
                return True
            except Exception as conn_e:
                print(f"Failed to connect to Kubernetes cluster: {conn_e}")
                raise Exception(f"Kubernetes cluster not reachable: {conn_e}")

        except Exception as e:
            print(f"Failed to setup Kubernetes client: {e}")
            raise Exception(f"Kubernetes cluster not available: {e}")

    async def create_test_namespace(self):
        """Create test namespace"""
        try:
            namespace_manifest = client.V1Namespace(
                metadata=client.V1ObjectMeta(
                    name=self.test_namespace,
                    labels={
                        "app": "devpocket-test",
                        "managed-by": "pytest",
                    },
                )
            )
            self.v1_core.create_namespace(body=namespace_manifest)
            self.created_resources.append(("namespace", self.test_namespace, None))
            return self.test_namespace
        except ApiException as e:
            if e.status == 409:  # Already exists
                return self.test_namespace
            raise

    async def cleanup_all_resources(self):
        """Clean up all created Kubernetes resources"""
        cleanup_errors = []

        # Clean up resources in reverse order
        for resource_type, name, namespace in reversed(self.created_resources):
            try:
                if resource_type == "namespace":
                    self.v1_core.delete_namespace(name=name)
                elif resource_type == "deployment":
                    self.v1_apps.delete_namespaced_deployment(
                        name=name, namespace=namespace
                    )
                elif resource_type == "service":
                    self.v1_core.delete_namespaced_service(
                        name=name, namespace=namespace
                    )
                elif resource_type == "configmap":
                    self.v1_core.delete_namespaced_config_map(
                        name=name, namespace=namespace
                    )
                elif resource_type == "pvc":
                    self.v1_core.delete_namespaced_persistent_volume_claim(
                        name=name, namespace=namespace
                    )
            except ApiException as e:
                if e.status != 404:  # Ignore not found errors
                    cleanup_errors.append(
                        f"Failed to delete {resource_type} {name}: {e}"
                    )

        # Wait for namespace deletion
        if cleanup_errors:
            print(f"Cleanup errors: {cleanup_errors}")

        # Wait a bit for resources to be cleaned up
        await asyncio.sleep(2)


@pytest_asyncio.fixture
async def k8s_manager():
    """Kubernetes test manager fixture"""
    manager = KubernetesTestManager()
    await manager.setup_kubernetes_client()  # This will raise exception if fails

    await manager.create_test_namespace()
    yield manager
    await manager.cleanup_all_resources()


@pytest_asyncio.fixture
async def test_cluster(clean_database):
    """Create a test cluster with local kubeconfig"""
    db = clean_database
    cluster_service.set_database(db)

    # Use the OVH kubeconfig
    try:
        ovh_kubeconfig = Path(__file__).parent.parent / "k8s" / "kube_config_ovh.yaml"
        if ovh_kubeconfig.exists():
            kubeconfig_path = str(ovh_kubeconfig)
            print(f"Using OVH kubeconfig from {kubeconfig_path}")
        else:
            # Fallback to default kubeconfig
            k8s_config.load_kube_config()
            kubeconfig_path = k8s_config.KUBE_CONFIG_DEFAULT_LOCATION
            if not os.path.exists(kubeconfig_path):
                kubeconfig_path = os.path.expanduser("~/.kube/config")
            print(f"Using default kubeconfig from {kubeconfig_path}")

        with open(kubeconfig_path, "r") as f:
            kubeconfig_content = f.read()

        # Encrypt kubeconfig using the same cipher suite as the cluster service
        from cryptography.fernet import Fernet

        # Create cipher suite with same logic as ClusterService
        encryption_key = settings.SECRET_KEY[:32].ljust(32, "0").encode()[:32]
        cipher_suite = Fernet(base64.urlsafe_b64encode(encryption_key))

        # Encrypt the kubeconfig content
        encrypted_kubeconfig = cipher_suite.encrypt(
            kubeconfig_content.encode()
        ).decode()

    except Exception as e:
        raise Exception(f"No kubeconfig available: {e}")

    # Create test cluster with correct field names for ClusterInDB model
    cluster_data = {
        "name": "test-local-cluster",
        "region": ClusterRegion.SOUTHEAST_ASIA,
        "provider": "local",
        "status": ClusterStatus.ACTIVE,
        "encrypted_kube_config": encrypted_kubeconfig,  # Properly encrypted kubeconfig
        "endpoint": "https://127.0.0.1:6443",  # Correct field name for ClusterInDB
        "description": "Local test cluster for integration tests",
        "node_count": 1,
        "version": "1.28",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "created_by": ObjectId(
            "000000000000000000000001"
        ),  # Required field for ClusterInDB
    }

    result = await db.clusters.insert_one(cluster_data)
    cluster_id = str(result.inserted_id)

    yield cluster_id

    # Cleanup
    await db.clusters.delete_one({"_id": result.inserted_id})


@pytest_asyncio.fixture
async def test_template(clean_database):
    """Create a test environment template"""
    db = clean_database
    template_service.set_database(db)

    template_data = {
        "name": "test-ubuntu",
        "display_name": "Test Ubuntu Environment",
        "description": "Ubuntu test environment with tmux",
        "category": "operating_system",
        "tags": ["ubuntu", "test", "tmux"],
        "docker_image": "ubuntu:22.04",
        "default_port": 8080,
        "default_resources": {"cpu": "100m", "memory": "256Mi", "storage": "1Gi"},
        "environment_variables": {
            "DEBIAN_FRONTEND": "noninteractive",
            "TERM": "xterm-256color",
            "USER": "devpocket",
            "HOME": "/home/devpocket",
        },
        "startup_commands": [
            "apt-get update",
            "apt-get install -y sudo curl wget git vim nano tmux",
            "useradd -m -s /bin/bash devpocket",
            "echo 'devpocket:devpocket' | chpasswd",
            "usermod -aG sudo devpocket",
            "echo 'devpocket ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers",
            "mkdir -p /home/devpocket/workspace",
            "chown -R devpocket:devpocket /home/devpocket",
        ],
        "documentation_url": "https://ubuntu.com/server/docs",
        "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/ubuntu/ubuntu-plain.svg",
    }

    template = await template_service.create_template_from_data(template_data)
    yield template

    # Cleanup
    await template_service.delete_template(template.id)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_environment_creation_full_workflow(
    clean_database, k8s_manager, test_cluster, test_template
):
    """Test complete environment creation workflow with Kubernetes resources"""
    db = clean_database
    environment_service.set_database(db)

    # Force real Kubernetes operations by temporarily disabling test mode
    import os

    original_testing = os.environ.get("TESTING", "")
    os.environ["TESTING"] = "false"

    try:
        # Create test environment
        test_user_id = str(ObjectId())
        environment_data = {
            "name": "test-env",
            "template": EnvironmentTemplate.UBUNTU,
            "user_id": test_user_id,
            "namespace": k8s_manager.test_namespace,
            "pod_name": f"test-env-{uuid.uuid4().hex[:8]}",
            "service_name": f"test-env-service",
            "status": EnvironmentStatus.CREATING,
            "resources": {"cpu": "100m", "memory": "256Mi", "storage": "1Gi"},
            "environment_variables": test_template.environment_variables,
        }

        # Insert environment to database
        result = await db.environments.insert_one(environment_data)
        environment_id = str(result.inserted_id)

        # Create environment record
        environment = EnvironmentInDB(
            id=environment_id,
            name=environment_data["name"],
            template=environment_data["template"],
            user_id=environment_data["user_id"],
            namespace=environment_data["namespace"],
            pod_name=environment_data["pod_name"],
            service_name=environment_data["service_name"],
            status=environment_data["status"],
            resources=ResourceLimits(**environment_data["resources"]),
            environment_variables=environment_data["environment_variables"],
        )

        # Create the actual environment (this will create K8s resources)
        await environment_service._create_container(environment)

        # Track created resources for cleanup
        k8s_manager.created_resources.extend(
            [
                (
                    "configmap",
                    f"env-{environment.pod_name}-init",
                    k8s_manager.test_namespace,
                ),
                ("pvc", f"home-{environment.pod_name}", k8s_manager.test_namespace),
                ("pvc", f"system-{environment.pod_name}", k8s_manager.test_namespace),
                ("deployment", environment.pod_name, k8s_manager.test_namespace),
                ("service", environment.service_name, k8s_manager.test_namespace),
            ]
        )

        # Wait a bit for resources to be created
        await asyncio.sleep(5)

        # Verify ConfigMap was created with correct data
        try:
            configmap = k8s_manager.v1_core.read_namespaced_config_map(
                name=f"env-{environment.pod_name}-init",
                namespace=k8s_manager.test_namespace,
            )
            assert configmap is not None
            assert "init.sh" in configmap.data
            assert "tmux.conf" in configmap.data
            assert "tmux" in configmap.data["init.sh"]  # Verify tmux setup is included
        except ApiException as e:
            pytest.fail(f"ConfigMap not found: {e}")

        # Verify PVCs were created
        try:
            home_pvc = k8s_manager.v1_core.read_namespaced_persistent_volume_claim(
                name=f"home-{environment.pod_name}",
                namespace=k8s_manager.test_namespace,
            )
            system_pvc = k8s_manager.v1_core.read_namespaced_persistent_volume_claim(
                name=f"system-{environment.pod_name}",
                namespace=k8s_manager.test_namespace,
            )
            assert home_pvc is not None
            assert system_pvc is not None
        except ApiException as e:
            pytest.fail(f"PVCs not found: {e}")

        # Verify Deployment was created
        try:
            deployment = k8s_manager.v1_apps.read_namespaced_deployment(
                name=environment.pod_name, namespace=k8s_manager.test_namespace
            )
            assert deployment is not None

            # Check that deployment uses ConfigMap volume
            volumes = deployment.spec.template.spec.volumes
            configmap_volume = None
            for volume in volumes:
                if volume.name == "init-scripts":
                    configmap_volume = volume
                    break

            assert configmap_volume is not None
            assert (
                configmap_volume.config_map.name == f"env-{environment.pod_name}-init"
            )

            # Check that container has proper volume mounts
            container = deployment.spec.template.spec.containers[0]
            volume_mounts = container.volume_mounts

            init_mount = None
            for mount in volume_mounts:
                if mount.name == "init-scripts":
                    init_mount = mount
                    break

            assert init_mount is not None
            assert init_mount.mount_path == "/etc/devpocket"

        except ApiException as e:
            pytest.fail(f"Deployment not found: {e}")

        # Verify Service was created
        try:
            service = k8s_manager.v1_core.read_namespaced_service(
                name=environment.service_name, namespace=k8s_manager.test_namespace
            )
            assert service is not None
        except ApiException as e:
            pytest.fail(f"Service not found: {e}")

        # Check environment status in database
        env_doc = await db.environments.find_one({"_id": result.inserted_id})
        assert env_doc is not None
        assert env_doc["status"] in [
            EnvironmentStatus.INSTALLING.value,
            EnvironmentStatus.CREATING.value,
            EnvironmentStatus.PROVISIONING.value,
        ]

    except Exception as e:
        # Log the error for debugging
        print(f"Error in test_environment_creation_full_workflow: {e}")
        # Re-raise the exception to fail the test properly
        raise
    finally:
        # Cleanup database
        await db.environments.delete_one({"_id": result.inserted_id})

        # Restore original TESTING environment variable
        if original_testing:
            os.environ["TESTING"] = original_testing
        else:
            os.environ.pop("TESTING", None)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_tmux_session_management():
    """Test tmux session creation and management"""
    test_env_id = str(uuid.uuid4())
    test_user_id = str(uuid.uuid4())

    # Test session creation (no initial command to keep session alive)
    session_id = await tmux_manager.create_session(
        environment_id=test_env_id, user_id=test_user_id, session_name="test-session"
    )

    # Session creation should succeed now that tmux is installed
    assert session_id is not None, "Failed to create tmux session"

    try:
        # Test session listing
        sessions = await tmux_manager.list_sessions(user_id=test_user_id)
        assert session_id in sessions

        # Test session input
        success = await tmux_manager.send_input(session_id, "echo 'test command'\n")
        assert success

        # Test session output capture
        output = await tmux_manager.capture_session_output(session_id)
        assert output is not None

        # Test session resize
        success = await tmux_manager.resize_session(session_id, 80, 24)
        assert success

    except Exception as e:
        # Log the error for debugging
        print(f"Error in test_tmux_session_management: {e}")
        # Re-raise the exception to fail the test properly
        raise
    finally:
        # Cleanup session
        await tmux_manager.kill_session(session_id)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_environment_logs_and_status(
    clean_database, k8s_manager, test_cluster, test_template
):
    """Test environment log streaming and status monitoring"""
    db = clean_database
    environment_service.set_database(db)

    # Create minimal test environment
    test_user_id = str(ObjectId())
    environment_data = {
        "name": "test-logs-env",
        "template": EnvironmentTemplate.UBUNTU,
        "user_id": test_user_id,
        "namespace": k8s_manager.test_namespace,
        "pod_name": f"test-logs-{uuid.uuid4().hex[:8]}",
        "service_name": f"test-logs-service",
        "status": EnvironmentStatus.CREATING,
        "resources": {"cpu": "100m", "memory": "256Mi", "storage": "1Gi"},
        "environment_variables": test_template.environment_variables,
    }

    result = await db.environments.insert_one(environment_data)
    environment_id = str(result.inserted_id)

    try:
        environment = EnvironmentInDB(
            id=environment_id,
            name=environment_data["name"],
            template=environment_data["template"],
            user_id=environment_data["user_id"],
            namespace=environment_data["namespace"],
            pod_name=environment_data["pod_name"],
            service_name=environment_data["service_name"],
            status=environment_data["status"],
            resources=ResourceLimits(**environment_data["resources"]),
            environment_variables=environment_data["environment_variables"],
        )

        # Create environment (minimal resource creation)
        await environment_service._create_container(environment)

        # Track resources for cleanup
        k8s_manager.created_resources.extend(
            [
                (
                    "configmap",
                    f"env-{environment.pod_name}-init",
                    k8s_manager.test_namespace,
                ),
                ("pvc", f"home-{environment.pod_name}", k8s_manager.test_namespace),
                ("pvc", f"system-{environment.pod_name}", k8s_manager.test_namespace),
                ("deployment", environment.pod_name, k8s_manager.test_namespace),
                ("service", environment.service_name, k8s_manager.test_namespace),
            ]
        )

        # Wait for pod to start
        await asyncio.sleep(10)

        # Test getting environment logs
        logs = await environment_service.get_environment_logs(
            environment_id, test_user_id
        )
        assert logs is not None

        # Check that environment status has been updated
        env_doc = await db.environments.find_one({"_id": result.inserted_id})
        assert env_doc["status"] in [
            EnvironmentStatus.INSTALLING.value,
            EnvironmentStatus.CREATING.value,
            EnvironmentStatus.PROVISIONING.value,
            EnvironmentStatus.RUNNING.value,
        ]

    except Exception as e:
        # Log the error for debugging
        print(f"Error in test_environment_logs_and_status: {e}")
        # Re-raise the exception to fail the test properly
        raise
    finally:
        # Cleanup
        await db.environments.delete_one({"_id": result.inserted_id})


@pytest.mark.asyncio
@pytest.mark.integration
async def test_template_loading_from_yaml():
    """Test loading templates from YAML files"""
    # Load templates from YAML files
    templates_dir = Path(__file__).parent.parent / "scripts" / "templates"

    if not templates_dir.exists():
        pytest.skip("Templates directory not found")

    yaml_files = list(templates_dir.glob("*.yaml"))
    assert len(yaml_files) > 0, "No template YAML files found"

    for yaml_file in yaml_files:
        with open(yaml_file, "r") as f:
            template_data = yaml.safe_load(f)

        # Validate required fields
        required_fields = ["name", "display_name", "description", "docker_image"]
        for field in required_fields:
            assert field in template_data, f"Template {yaml_file.name} missing {field}"

        # Validate tmux is included in startup commands
        startup_commands = template_data.get("startup_commands", [])
        has_tmux = any("tmux" in cmd for cmd in startup_commands)
        assert has_tmux, f"Template {yaml_file.name} should include tmux installation"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
