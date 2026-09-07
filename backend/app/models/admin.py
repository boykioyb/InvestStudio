"""Nhật ký kiểm toán + cấu hình chạy (cần gạt khẩn cấp).

`audit_logs` CHỈ GHI THÊM — không sửa, không xóa. Nó là bằng chứng bảo vệ chính
người vận hành khi có tranh chấp ("ai đã xem dữ liệu của tôi?"), và là thứ được
hỏi đầu tiên nếu xảy ra lộ dữ liệu.

`app_settings` cho phép đổi hạn mức và TẮT tính năng ngay trong /admin mà không
cần deploy lại — thứ duy nhất cứu được khi đang bị lạm dụng lúc 2h sáng.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_at", "at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actor_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_email: Mapped[str] = mapped_column(String(255), default="")
    actor_ip: Mapped[str] = mapped_column(String(45), default="")
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), default="")
    target_id: Mapped[str] = mapped_column(String(64), default="")
    before: Mapped[dict] = mapped_column(JSONB, default=dict)
    after: Mapped[dict] = mapped_column(JSONB, default=dict)
    reason: Mapped[str] = mapped_column(Text, default="")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB, default=dict)   # {"v": <giá trị>}
    updated_by: Mapped[str] = mapped_column(String(255), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                 server_default=func.now(), onupdate=func.now())
