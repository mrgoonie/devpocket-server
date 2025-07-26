from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from bson import ObjectId


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


class ClusterStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class ClusterRegion(str, Enum):
    US_EAST = "us-east"
    US_WEST = "us-west"
    EU_CENTRAL = "eu-central"
    ASIA_PACIFIC = "asia-pacific"
    SOUTHEAST_ASIA = "southeast-asia"


class ClusterBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    region: ClusterRegion
    description: Optional[str] = Field(None, max_length=200)
    endpoint: str = Field(..., description="Kubernetes API server endpoint")
    is_default: bool = False
    max_environments: int = Field(default=100, ge=1, le=1000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "Cluster name must be alphanumeric with optional hyphens and underscores"
            )
        return v


class ClusterCreate(ClusterBase):
    kube_config: str = Field(..., description="Base64 encoded kubeconfig content")


class ClusterUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    endpoint: Optional[str] = None
    is_default: Optional[bool] = None
    max_environments: Optional[int] = None
    status: Optional[ClusterStatus] = None
    kube_config: Optional[str] = None


class ClusterInDB(ClusterBase):
    id: PyObjectId = Field(alias="_id")
    encrypted_kube_config: str = Field(..., description="Encrypted kubeconfig content")
    status: ClusterStatus = ClusterStatus.ACTIVE
    environments_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: PyObjectId

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class ClusterResponse(ClusterBase):
    id: str
    status: ClusterStatus
    environments_count: int
    created_at: datetime
    updated_at: datetime


class ClusterHealthCheck(BaseModel):
    cluster_id: str
    status: ClusterStatus
    last_check: datetime
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    node_count: Optional[int] = None
    available_resources: Optional[Dict[str, Any]] = None
