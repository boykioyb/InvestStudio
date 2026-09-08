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


# ── Hội thoại ────────────────────────────────────────────────────────────────

class AdminConversation(BaseModel):
    """Metadata một cuộc trò chuyện. Nội dung xem ở endpoint riêng (ghi audit)."""

    id: int
    user_id: int
    user_email: str = ""
    title: str
    ticker: Optional[str] = None
    message_count: int = 0
    updated_at: datetime


class AdminMessage(BaseModel):
    id: int
    at: datetime
    ticker: Optional[str] = None
    question: str
    answer: str
    citations: list = []
    attachments: list = []


class ChatSearchHit(BaseModel):
    message_id: int
    conversation_id: Optional[int] = None
    user_id: int
    user_email: str = ""
    at: datetime
    ticker: Optional[str] = None
    #  Đoạn khớp, đã cắt ngắn — muốn xem đủ thì mở cả cuộc trò chuyện.
    snippet: str


# ── Thiết bị ─────────────────────────────────────────────────────────────────

class AdminDevice(BaseModel):
    model_config = {"from_attributes": True}

    fp_hash: str
    first_seen: datetime
    last_seen: datetime
    user_agent: str = ""
    last_ip: str = ""
    request_count: int = 0
    account_count: int = 0
    blocked: bool = False
    blocked_reason: str = ""
    emails: list[str] = []


class DeviceBlockIn(BaseModel):
    reason: str = Field("", max_length=300)


# ── Kho tri thức (RAG) ───────────────────────────────────────────────────────

class RagDocOut(BaseModel):
    id: int
    ticker: str
    doc_type: str
    title: str
    created_at: datetime
    chars: int


class RagStatusOut(BaseModel):
    documents: int
    tickers: int
    running: bool
    last_message: str = ""
    #  Tài liệu cũ nhất bao nhiêu ngày — kho đứng yên là trợ lý trả lời bằng dữ
    #  liệu cũ mà không ai biết.
    oldest_days: Optional[int] = None
    newest_days: Optional[int] = None
    by_type: dict[str, int] = {}


# ── Job & hàng đợi ───────────────────────────────────────────────────────────

class JobOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    task_id: str
    status: str
    message: str = ""
    created_at: datetime
    updated_at: datetime


class QueueOut(BaseModel):
    jobs: list[JobOut]
    queue_length: int = 0
    #  Redis hỏng thì không đọc được độ dài hàng đợi — nói thật thay vì trả 0.
    queue_ok: bool = True


# ── Nguồn dữ liệu ────────────────────────────────────────────────────────────

class ProviderOut(BaseModel):
    name: str
    ok: bool
    latency_ms: int
    detail: str = ""
    checked_at: datetime


# ── Cache ────────────────────────────────────────────────────────────────────

class CacheOut(BaseModel):
    name: str
    size: int
    maxsize: int
    ttl_seconds: int


class CacheReport(BaseModel):
    caches: list[CacheOut]
    #  Cảnh báo bắt buộc: cache nằm TRONG tiến trình, nhiều worker thì mỗi worker
    #  một bản — số ở đây là của đúng tiến trình vừa trả lời request này.
    note: str


# ── Thông báo hệ thống ───────────────────────────────────────────────────────

class BroadcastIn(BaseModel):
    message: str = Field(..., min_length=5, max_length=500)
    only_verified: bool = Field(True, description="Chỉ gửi cho tài khoản đã xác minh email")


class BroadcastOut(BaseModel):
    sent: int
