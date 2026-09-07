"""Bảng người dùng và danh sách mã yêu thích / theo dõi."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
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
    #  'user' | 'admin'. Chỉ admin được chạm vào việc tiêu hạn mức chung (lập
    #  chỉ mục RAG) — xem app/api/deps.py:require_admin.
    role: Mapped[str] = mapped_column(String(16), default="user", server_default="user",
                                      nullable=False)
    #  'active' | 'suspended'. Khóa tài khoản mà không xóa dữ liệu.
    status: Mapped[str] = mapped_column(String(16), default="active", server_default="active",
                                        nullable=False)
    #  None = chưa xác minh email → chưa được dùng trợ lý (chống tạo tài khoản
    #  hàng loạt để nhân hạn mức).
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    #  Tăng lên là MỌI token đã cấp hết hiệu lực ngay (đổi mật khẩu, bị khóa,
    #  nghi lộ phiên). Token sống 7 ngày nên không có cái này thì đổi mật khẩu
    #  gần như vô nghĩa trước kẻ đã trộm được cookie.
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0",
                                               nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    last_ip: Mapped[str] = mapped_column(String(45), default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def email_verified(self) -> bool:
        """Cho DTO `UserOut` đọc — frontend chỉ cần biết đã xác minh hay chưa."""
        return self.email_verified_at is not None

    watchlist: Mapped[list["WatchlistItem"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", order_by="WatchlistItem.created_at",
    )


class WatchlistItem(Base):
    """Một mã người dùng ghim để theo dõi nhanh.

    `target_price` / `target_score` là NGƯỠNG người dùng tự đặt để theo dõi.
    Job nền `watchlist.check_alerts` (Celery Beat, mỗi 30') so ngưỡng này với
    giá/điểm hiện tại rồi tạo `Notification` (xem `core/celery_app.py`).
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
