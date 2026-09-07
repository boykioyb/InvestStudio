"""Schema cho các khối dữ liệu THỊ TRƯỜNG dùng chung (trang chủ).

Để riêng khỏi `stock.py` vì đây là dữ liệu theo RỔ (nhiều mã), không phải theo
một mã. `Level` vẫn dùng lại kiểu chung của `stock.py` — màu sắc trong toàn app
chỉ có một bộ quy ước.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.stock import Level


class HighlightEvent(BaseModel):
    """Một sự kiện doanh nghiệp SẮP TỚI (ngày GDKHQ còn ở tương lai).

    `level` do BACKEND phân loại (xem `highlights._level`) — frontend chỉ tô màu
    theo nhãn này, không tự đoán từ chữ nghĩa trong `kind`/`detail`.
    """

    date: str = Field(..., description="Ngày GDKHQ (giao dịch không hưởng quyền), YYYY-MM-DD")
    symbol: str = Field(..., description="Mã chứng khoán")
    kind: str = Field(..., description="Loại sự kiện đã rút gọn, VD 'Cổ tức tiền'")
    detail: str = Field("", description="Nội dung sự kiện theo công bố của nguồn")
    level: Level = Field(..., description="good = cổ đông được nhận · warn = cần đọc kỹ · bad = xấu")


class HighlightNews(BaseModel):
    """Một tin công bố mới nhất của mã trong rổ."""

    symbol: str = Field(..., description="Mã chứng khoán tin này gắn với")
    title: str = Field(..., description="Tiêu đề tin")
    date: str = Field("", description="Ngày đăng YYYY-MM-DD")
    url: Optional[str] = Field(None, description="Link bài gốc; None nếu nguồn không có")


class LeaderRow(BaseModel):
    """Một dòng bảng điểm — điểm lấy TỪ mô hình 100 điểm (`services/scoring.py`)."""

    symbol: str = Field(..., description="Mã chứng khoán")
    score: int = Field(..., description="Tổng điểm 0–100 của mô hình 14 tiêu chí")


class MarketHighlights(BaseModel):
    """Ba khối điểm nhấn của trang chủ.

    Cả ba mảng ĐỀU CÓ THỂ RỖNG: nguồn không trả được thì để trống, tuyệt đối
    không bịa số liệu. `leaders` còn có thể chỉ có vài dòng vì việc chấm điểm
    tốn nhiều request — xem ghi chú trong `services/highlights.py`.
    """

    group: str = Field(..., description="Rổ đang xem, VD VN30")
    events: list[HighlightEvent] = Field(default_factory=list)
    news: list[HighlightNews] = Field(default_factory=list)
    leaders: list[LeaderRow] = Field(default_factory=list)
