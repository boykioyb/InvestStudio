"""Danh mục cổ phiếu đồng bộ từ công ty chứng khoán (VD TCBS/TCInvest).

Vì sao lưu server-side (khác với danh mục nhập tay đang giữ ở localStorage của
trình duyệt): nguồn dữ liệu là extension chạy trên trang TCInvest — KHÁC origin
với InvestStudio nên không ghi thẳng vào localStorage được. Extension gửi danh
mục qua `POST /api/portfolio/import`, ta lưu theo user để trang web đọc lại và
chấm điểm từng mã.

Chỉ lưu số lượng + giá vốn + giá thị trường tại thời điểm đồng bộ. KHÔNG lưu
token TCBS, KHÔNG lưu bất cứ thứ gì đăng nhập được vào tài khoản chứng khoán.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ImportedHolding(Base):
    """Một vị thế cổ phiếu đồng bộ về từ công ty chứng khoán."""

    __tablename__ = "imported_holdings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    ticker: Mapped[str] = mapped_column(String(12), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    #  Giá vốn / giá thị trường lưu theo ĐỒNG (như nguồn TCBS trả về), frontend tự
    #  quy đổi hiển thị. None = nguồn không cung cấp.
    avg_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    #  Lãi/lỗ ĐÃ THỰC HIỆN (đồng) — từ portfolio_gainloss của TCBS. None = không đồng bộ.
    realized_pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="TCBS")
    account_no: Mapped[str] = mapped_column(String(24), default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ImportedLot(Base):
    """Một ĐỢT KHỚP (mua/bán) đồng bộ từ lịch sử lệnh của công ty chứng khoán.

    Dùng để dựng lại 'Vị thế của tôi' theo từng đợt mua, thay vì chỉ giá vốn bình
    quân. Giá lưu theo ĐỒNG (matchPrice của TCBS). Lưu đè theo user mỗi lần đồng bộ.
    """

    __tablename__ = "imported_lots"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    ticker: Mapped[str] = mapped_column(String(12), nullable=False)
    side: Mapped[str] = mapped_column(String(4), default="buy")  # 'buy' | 'sell'
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    price: Mapped[float] = mapped_column(Float, default=0.0)      # đồng/cp
    fee: Mapped[float | None] = mapped_column(Float, nullable=True)
    tax: Mapped[float | None] = mapped_column(Float, nullable=True)
    txdate: Mapped[str] = mapped_column(String(16), default="")
    order_id: Mapped[str] = mapped_column(String(32), default="")
    source: Mapped[str] = mapped_column(String(16), default="TCBS")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())
