"""Authentication schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr, field_validator


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters")
        if len(v) > 128:
            raise ValueError("Password must not exceed 128 characters")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserResponseSafe(BaseModel):
    """Safe user response without sensitive fields."""
    id: int
    email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AuthError(BaseModel):
    detail: str