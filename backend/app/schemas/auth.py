"""Schema (DTO) cho đăng ký / đăng nhập / thông tin người dùng."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128,
                          description="Mật khẩu tối thiểu 6 ký tự")
    display_name: str = Field("", max_length=120, description="Tên hiển thị (tùy chọn)")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=6, max_length=128,
                              description="Mật khẩu mới tối thiểu 6 ký tự")


class UserOut(BaseModel):
    """Thông tin an toàn để lộ ra frontend — KHÔNG bao giờ kèm mật khẩu."""

    model_config = {"from_attributes": True}

    id: int
    email: EmailStr
    display_name: str
    created_at: datetime
