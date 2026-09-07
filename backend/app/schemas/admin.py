"""DTO cho khu quản trị."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AdminUserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    email: str
    display_name: str
    role: str
    status: str
    email_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    last_ip: str = ""
    watchlist_count: int = 0
    chat_count: int = 0
    device_count: int = 0


class AdminUserList(BaseModel):
    items: list[AdminUserOut]
    total: int
    page: int
    pages: int


class AdminUserPatch(BaseModel):
    """Chỉ những trường quản trị được đổi. Mọi thay đổi đều ghi audit."""

    role: Optional[str] = Field(None, pattern="^(user|admin)$")
    status: Optional[str] = Field(None, pattern="^(active|suspended)$")
    email_verified: Optional[bool] = None
    reason: str = Field("", max_length=500)


class UsagePoint(BaseModel):
    day: date
    kind: str
    count: int = 0
    calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    error_count: int = 0


class TopEntry(BaseModel):
    key: str
    label: str = ""
    count: int


class OverviewOut(BaseModel):
    """Thẻ số + chuỗi thời gian cho trang Tổng quan."""

    users_total: int
    users_new_today: int
    users_verified: int
    active_today: int              # số tài khoản có hoạt động tốn hạn mức hôm nay
    chat_today: int
    analyze_today: int
    gemini_used: int               # request Gemini đã dùng hôm nay
    gemini_cap: int
    gemini_ratio: float
    gemini_level: str              # ok | saving | exhausted
    error_rate_today: float
    rag_documents: int
    rag_tickers: int
    queue_running: bool
    series: list[UsagePoint]
    top_users: list[TopEntry]
    top_tickers: list[TopEntry]


class SettingOut(BaseModel):
    key: str
    label: str
    group: str
    type: str
    value: Any
    overridden: bool


class SettingsPut(BaseModel):
    values: dict[str, Any]
    reason: str = Field("", max_length=500)


class AuditOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    at: datetime
    actor_email: str
    actor_ip: str
    action: str
    target_type: str
    target_id: str
    before: dict = {}
    after: dict = {}
    reason: str = ""


class TotpSetupOut(BaseModel):
    secret: str
    otpauth_url: str
    note: str = ("Quét mã bằng ứng dụng xác thực (Google Authenticator, Authy…) rồi "
                 "nhập mã 6 số để bật.")
