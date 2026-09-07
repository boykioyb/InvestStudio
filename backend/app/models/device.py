"""Dấu vân tay thiết bị — đếm hạn mức theo THIẾT BỊ, không chỉ theo tài khoản.

Vì sao cần: hạn mức theo tài khoản bị vô hiệu chỉ bằng việc đăng ký thêm email.
Đếm thêm theo thiết bị thì đổi tài khoản, xóa cookie, mở tab ẩn danh hay đổi IP
đều vẫn rơi vào cùng một rổ.

Giới hạn phải biết trước (đã ghi trong docs/SHIP_PLAN.md §2.4): đổi trình duyệt,
bật chống-fingerprint của Brave/Firefox, hoặc dùng máy khác thì vân tay đổi hẳn.
Đây là lớp MA SÁT, không phải lớp bảo đảm — lớp bảo đảm là trần toàn cục ở
app/core/budget.py.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DeviceFingerprint(Base):
    __tablename__ = "device_fingerprints"

    #  sha256 của (visitorId của thư viện + id thiết bị server cấp + UA + ngôn ngữ).
    fp_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                 server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                server_default=func.now(), onupdate=func.now())
    user_agent: Mapped[str] = mapped_column(String(300), default="")
    accept_language: Mapped[str] = mapped_column(String(120), default="")
    last_ip: Mapped[str] = mapped_column(String(45), default="")
    request_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    #  Số TÀI KHOẢN từng đăng nhập trên thiết bị này — cột đáng ngờ nhất khi soi
    #  người tạo tài khoản hàng loạt.
    account_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    blocked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    blocked_reason: Mapped[str] = mapped_column(Text, default="")
    note: Mapped[str] = mapped_column(Text, default="")


class DeviceAccount(Base):
    """Bảng nối thiết bị ↔ tài khoản: soi được cụm tài khoản dùng chung một máy."""

    __tablename__ = "device_accounts"

    fp_hash: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                 server_default=func.now())
