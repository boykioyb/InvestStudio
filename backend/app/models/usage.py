"""Số liệu sử dụng: sự kiện TỐN HẠN MỨC + bảng tổng hợp theo ngày.

Hai tầng cố ý:

- `usage_events` — mỗi dòng là MỘT việc đắt (gọi Gemini, crawl thật). KHÔNG ghi
  cho mọi request: một trang có hàng chục lời gọi API, ghi hết thì bảng này
  thành nút thắt của chính hệ thống.
- `usage_daily` — bảng tổng hợp cho biểu đồ 30 ngày ở /admin, để trang quản trị
  không phải quét bảng thô mỗi lần mở.

KHÔNG có cột tiền: Gemini đang chạy bản miễn phí, không có hóa đơn. Token vẫn
lưu vì bản miễn phí còn trần TPM (token/phút) — cần biết còn cách trần bao xa.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UsageEvent(Base):
    __tablename__ = "usage_events"
    __table_args__ = (
        Index("ix_usage_events_at", "at"),
        Index("ix_usage_events_user_at", "user_id", "at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    #  Không dùng khóa ngoại: xóa tài khoản thì số liệu tổng hợp vẫn phải đúng,
    #  chỉ mất phần định danh.
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ip: Mapped[str] = mapped_column(String(45), default="")
    fp_hash: Mapped[str] = mapped_column(String(64), default="")
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # chat|analyze|embed|admin
    ticker: Mapped[str] = mapped_column(String(12), default="")
    calls: Mapped[int] = mapped_column(Integer, default=0)         # số request Gemini thật
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="ok")  # ok|error|quota


class UsageDaily(Base):
    """Tổng hợp theo (ngày, loại, người dùng). `user_id = 0` nghĩa là TỔNG cả ngày."""

    __tablename__ = "usage_daily"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, default=0)
    count: Mapped[int] = mapped_column(Integer, default=0)
    calls: Mapped[int] = mapped_column(Integer, default=0)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
