"""Sự kiện SẢN PHẨM (hành vi người dùng) để đo North Star Metric.

TÁCH KHỎI `usage_events` một cách có chủ đích:

- `usage_events` đo **CHI PHÍ** (gọi Gemini, crawl thật) phục vụ hạn mức/quota —
  chỉ ghi cho việc ĐẮT, và /admin cộng token/calls theo `kind` trên bảng đó.
- `product_events` (bảng này) đo **GIÁ TRỊ**: người dùng có thực sự phân tích mã,
  có mở phần "vì sao điểm", có hành động sau khi xem điểm không. Đây là dữ liệu
  để trả lời North Star Metric và kiểm chứng giả định nguy hiểm nhất
  ("user có tin điểm máy chấm không").

Vì sao không nhét chung vào `usage_events`: sự kiện giao diện (mở popover) rẻ và
tần suất cao — trộn vào sẽ (1) làm phình bảng vốn để truy vết chi phí và (2) làm
bẩn biểu đồ token/calls ở /admin. Hai mục đích khác nhau → hai bảng.

Danh tính để đếm "người dùng riêng biệt": ưu tiên `user_id` (đã đăng nhập); khách
thì rơi về `fp_hash` — vân tay THIẾT BỊ đã có sẵn cho hạn mức, KHÔNG thêm bề mặt
thu thập dữ liệu mới (xem app/core/fingerprint.py).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProductEvent(Base):
    __tablename__ = "product_events"
    __table_args__ = (
        #  Truy vấn NSM luôn lọc theo (loại sự kiện, khoảng thời gian).
        Index("ix_product_events_event_at", "event", "at"),
        #  Đếm "người dùng hoạt động" theo user trong một khoảng thời gian.
        Index("ix_product_events_user_at", "user_id", "at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    #  Không dùng khóa ngoại: xóa tài khoản thì số liệu tổng hợp vẫn đúng.
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #  Danh tính khách (dedup người dùng ẩn danh trong một khoảng thời gian).
    fp_hash: Mapped[str] = mapped_column(String(64), default="")
    #  analyze | assistant | why_open | score_action
    event: Mapped[str] = mapped_column(String(24), nullable=False)
    ticker: Mapped[str] = mapped_column(String(12), default="")
    #  Ngữ cảnh phụ: nhãn tiêu chí được mở, 'total', hay loại hành động ('watch').
    ref: Mapped[str] = mapped_column(String(48), default="")
