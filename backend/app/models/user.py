"""Bảng người dùng và danh sách mã yêu thích / theo dõi."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    #  Tên hiển thị (tùy chọn) — mặc định lấy phần trước @ của email.
    display_name: Mapped[str] = mapped_column(String(120), default="")
    #  Chỉ lưu MẬT KHẨU ĐÃ BĂM (bcrypt), không bao giờ lưu mật khẩu thô.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    watchlist: Mapped[list["WatchlistItem"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", order_by="WatchlistItem.created_at",
    )


class WatchlistItem(Base):
    """Một mã người dùng ghim để theo dõi nhanh.

    `target_price` / `target_score` là NGƯỠNG người dùng tự đặt để theo dõi —
    hiện chỉ LƯU LẠI, chưa có job nền tự bắn cảnh báo (để giai đoạn sau).
    """

    __tablename__ = "watchlist_items"
    __table_args__ = (
        #  Mỗi người chỉ ghim một mã một lần.
        UniqueConstraint("user_id", "ticker", name="uq_watchlist_user_ticker"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    ticker: Mapped[str] = mapped_column(String(12), nullable=False)
    note: Mapped[str] = mapped_column(Text, default="")
    target_price: Mapped[float | None] = mapped_column(Float, nullable=True)  # nghìn đ
    target_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # /100
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="watchlist")


class Notification(Base):
    """Thông báo trong app (kênh MVP cho cảnh báo ngưỡng theo dõi).

    Job nền tạo thông báo khi giá/điểm của mã đạt ngưỡng người dùng đặt; frontend
    hiển thị và đánh dấu đã đọc. Email/web push để giai đoạn sau.
    """

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    ticker: Mapped[str] = mapped_column(String(12), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # 'price' | 'score'
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
