from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class AdminCreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    roles: list[str] = Field(min_length=1)


class AdminUpdateRolesRequest(BaseModel):
    roles: list[str] = Field(min_length=1)


class AdminUserResponse(BaseModel):
    id: UUID
    organization_id: UUID
    email: EmailStr
    full_name: str
    status: str
    roles: list[str]
    created_at: datetime


class AppConfigResponse(BaseModel):
    id: UUID
    organization_id: UUID
    version: int
    is_active: bool
    config_json: dict[str, Any]
    updated_by: str
    created_at: datetime


class AppConfigUpdateRequest(BaseModel):
    config_json: dict[str, Any]
