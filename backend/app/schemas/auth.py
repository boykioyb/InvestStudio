"""Schema (DTO) cho đăng ký / đăng nhập / thông tin người dùng."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


#  Tối thiểu 10 ký tự: 6 ký tự dò được trong vài giờ bằng máy thường. Không ép
#  thêm quy tắc "phải có ký tự đặc biệt" — độ DÀI mới là thứ quyết định, còn quy
#  tắc rườm rà chỉ đẩy người dùng sang "Matkhau@123".
_MIN_PASSWORD = 10


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=_MIN_PASSWORD, max_length=128,
                          description=f"Mật khẩu tối thiểu {_MIN_PASSWORD} ký tự")
    display_name: str = Field("", max_length=120, description="Tên hiển thị (tùy chọn)")
    #  Chỉ cần khi thiết bị đã tạo nhiều tài khoản — xem GET /auth/challenge.
    pow_nonce: str = Field("", max_length=64)
    pow_answer: str = Field("", max_length=64)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)
    #  Mã 6 số từ ứng dụng xác thực — bắt buộc với tài khoản quản trị đã bật 2 lớp.
    totp_code: str = Field("", max_length=8)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=_MIN_PASSWORD, max_length=128,
                              description=f"Mật khẩu mới tối thiểu {_MIN_PASSWORD} ký tự")


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=2000)
    new_password: str = Field(..., min_length=_MIN_PASSWORD, max_length=128)


class PreferencesRequest(BaseModel):
    """Tùy chọn cá nhân — hiện chỉ có công tắc email cảnh báo."""

    alert_email: bool


class DeleteAccountRequest(BaseModel):
    """Xóa tài khoản: bắt nhập lại mật khẩu — thao tác không hoàn tác được."""

    password: str = Field(..., min_length=1, max_length=128)


class UserOut(BaseModel):
    """Thông tin an toàn để lộ ra frontend — KHÔNG bao giờ kèm mật khẩu."""

    model_config = {"from_attributes": True}

    id: int
    email: EmailStr
    display_name: str
    role: str = "user"
    email_verified: bool = False
    totp_enabled: bool = False
    alert_email: bool = True
    #  'password' | 'google' — để frontend biết tài khoản đăng nhập kiểu nào.
    auth_provider: str = "password"
    #  False với tài khoản Google chưa đặt mật khẩu → ẩn ô đổi mật khẩu.
    has_password: bool = True
    created_at: datetime
