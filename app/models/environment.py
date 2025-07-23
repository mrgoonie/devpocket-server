from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema
        return core_schema.str_schema()

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

class EnvironmentStatus(str, Enum):
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    TERMINATED = "terminated"
    ERROR = "error"

class EnvironmentTemplate(str, Enum):
    PYTHON = "python"
    NODEJS = "nodejs"
    GOLANG = "golang"
    RUST = "rust"
    UBUNTU = "ubuntu"
    CUSTOM = "custom"

class ResourceLimits(BaseModel):
    cpu: str = "500m"  # 500 millicores
    memory: str = "1Gi"  # 1 Gigabyte
    storage: str = "10Gi"  # 10 Gigabytes
    
    @field_validator("cpu")
    @classmethod
    def validate_cpu(cls, v):
        if not v.endswith("m") and not v.isdigit():
            raise ValueError("CPU must be in millicores (e.g., '500m') or cores (e.g., '1')")
        return v
    
    @field_validator("memory", "storage")
    @classmethod
    def validate_memory_storage(cls, v):
        valid_units = ["Ki", "Mi", "Gi", "Ti"]
        if not any(v.endswith(unit) for unit in valid_units):
            raise ValueError("Memory/Storage must end with Ki, Mi, Gi, or Ti")
        return v

class EnvironmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    template: EnvironmentTemplate = EnvironmentTemplate.UBUNTU
    resources: Optional[ResourceLimits] = None
    environment_variables: Optional[Dict[str, str]] = {}
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        # Environment name should be DNS compatible
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Name must be alphanumeric with optional hyphens and underscores")
        if v.startswith("-") or v.endswith("-"):
            raise ValueError("Name cannot start or end with hyphen")
        return v.lower()

class EnvironmentUpdate(BaseModel):
    name: Optional[str] = None
    resources: Optional[ResourceLimits] = None
    environment_variables: Optional[Dict[str, str]] = None

class EnvironmentInDB(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: str
    name: str
    template: EnvironmentTemplate
    status: EnvironmentStatus = EnvironmentStatus.CREATING
    resources: ResourceLimits
    environment_variables: Dict[str, str] = {}
    
    # Container/Kubernetes specific fields
    container_id: Optional[str] = None
    namespace: Optional[str] = None
    pod_name: Optional[str] = None
    service_name: Optional[str] = None
    
    # Network and access info
    internal_url: Optional[str] = None
    external_url: Optional[str] = None
    ssh_port: Optional[int] = None
    web_port: Optional[int] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: Optional[datetime] = None
    
    # Usage tracking
    cpu_usage: Optional[float] = 0.0  # percentage
    memory_usage: Optional[float] = 0.0  # percentage
    storage_usage: Optional[float] = 0.0  # percentage
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

class EnvironmentResponse(BaseModel):
    id: str
    name: str
    template: EnvironmentTemplate
    status: EnvironmentStatus
    resources: ResourceLimits
    external_url: Optional[str]
    web_port: Optional[int]
    created_at: datetime
    last_accessed: Optional[datetime]
    cpu_usage: Optional[float]
    memory_usage: Optional[float]
    storage_usage: Optional[float]

class WebSocketSession(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: str
    environment_id: str
    connection_id: str
    connected_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

class EnvironmentMetrics(BaseModel):
    environment_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    cpu_usage: float
    memory_usage: float
    storage_usage: float
    network_rx: Optional[float] = 0.0  # bytes received
    network_tx: Optional[float] = 0.0  # bytes transmitted
    active_connections: int = 0