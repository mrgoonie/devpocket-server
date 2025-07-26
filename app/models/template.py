from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema

        return core_schema.no_info_before_validator_function(
            cls.validate,
            core_schema.str_schema(),
        )

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str):
            if not ObjectId.is_valid(v):
                raise ValueError("Invalid ObjectId")
            return v
        raise ValueError("ObjectId must be a valid ObjectId or string")

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema, handler):
        field_schema.update(type="string")


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


class TemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    category: TemplateCategory
    tags: List[str] = []
    docker_image: str = Field(..., description="Docker image for the template")
    default_port: Optional[int] = 8080
    default_resources: Dict[str, str] = {
        "cpu": "500m",
        "memory": "1Gi",
        "storage": "10Gi",
    }
    environment_variables: Dict[str, str] = {}
    startup_commands: List[str] = []
    documentation_url: Optional[str] = None
    icon_url: Optional[str] = None


class TemplateCreate(TemplateBase):
    class Config:
        json_schema_extra = {
            "example": {
                "name": "java",
                "display_name": "Java 17 LTS",
                "description": "Java development environment with Maven and Gradle support",
                "category": "programming_language",
                "tags": ["java", "jvm", "maven", "gradle", "spring"],
                "docker_image": "openjdk:17-slim",
                "default_port": 8080,
                "default_resources": {
                    "cpu": "1000m",
                    "memory": "2Gi",
                    "storage": "15Gi",
                },
                "environment_variables": {
                    "JAVA_HOME": "/usr/local/openjdk-17",
                    "MAVEN_HOME": "/usr/share/maven",
                },
                "startup_commands": [
                    "apt-get update && apt-get install -y maven gradle",
                    "mkdir -p /workspace",
                ],
                "documentation_url": "https://docs.oracle.com/en/java/",
                "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/java/java-original.svg",
            }
        }


class TemplateUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    docker_image: Optional[str] = None
    default_port: Optional[int] = None
    default_resources: Optional[Dict[str, str]] = None
    environment_variables: Optional[Dict[str, str]] = None
    startup_commands: Optional[List[str]] = None
    documentation_url: Optional[str] = None
    icon_url: Optional[str] = None
    status: Optional[TemplateStatus] = None

    class Config:
        json_schema_extra = {
            "example": {
                "description": "Updated Java development environment with Spring Boot support",
                "tags": ["java", "spring-boot", "microservices"],
                "environment_variables": {
                    "JAVA_HOME": "/usr/local/openjdk-17",
                    "SPRING_PROFILES_ACTIVE": "dev",
                },
                "status": "active",
            }
        }


class TemplateInDB(TemplateBase):
    id: PyObjectId = Field(alias="_id")
    status: TemplateStatus = TemplateStatus.ACTIVE
    version: str = "1.0.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: PyObjectId
    usage_count: int = 0

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class TemplateResponse(TemplateBase):
    id: str
    status: TemplateStatus
    version: str
    created_at: datetime
    updated_at: datetime
    usage_count: int


class LogEntry(BaseModel):
    timestamp: datetime
    level: str  # INFO, ERROR, WARNING, DEBUG
    message: str
    source: Optional[str] = None  # container, system, application


class EnvironmentLogs(BaseModel):
    environment_id: str
    logs: List[LogEntry]
    total_lines: int
    has_more: bool = False
