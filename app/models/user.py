from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from .cluster import ClusterRegion


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


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=100)
    preferred_region: Optional[ClusterRegion] = ClusterRegion.US_EAST

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v):
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Username must be alphanumeric with optional underscores and hyphens"
            )
        return v


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    preferred_region: Optional[ClusterRegion] = None


class UserInDB(UserBase):
    id: str = Field(alias="_id")
    hashed_password: str
    is_active: bool = True
    is_verified: bool = False
    google_id: Optional[str] = None
    avatar_url: Optional[str] = None
    subscription_plan: str = "free"  # free, starter, pro
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    email_verification_token: Optional[str] = None
    email_verification_expires: Optional[datetime] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class UserResponse(UserBase):
    id: str
    is_active: bool
    is_verified: bool
    avatar_url: Optional[str]
    subscription_plan: str
    created_at: datetime
    last_login: Optional[datetime]


class UserLogin(BaseModel):
    username_or_email: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class EmailVerificationRequest(BaseModel):
    token: str


class TokenData(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None


class GoogleUserInfo(BaseModel):
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    verified_email: bool = False
