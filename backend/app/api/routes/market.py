"""Route dữ liệu thị trường dùng chung (theo RỔ, không theo một mã).

  · /quotes     — giá khớp gần realtime cho frontend poll
  · /highlights — ba khối điểm nhấn trang chủ (sự kiện · tin · bảng điểm)
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.market import MarketHighlights
from app.schemas.stock import QuoteBatch
from app.services import highlights, quote, screener

router = APIRouter(prefix="/market", tags=["market"])

_MAX_SYMBOLS = 50  # trần một lần gọi — chặn lạm dụng, đủ cho một watchlist

#  Dùng CHUNG danh sách rổ với /api/screener — hai nơi khai báo khác nhau thì
#  frontend sẽ gửi được rổ hợp lệ ở màn này mà lỗi ở màn kia.
_GROUP_KEYS = tuple(group.key for group in screener.GROUPS)


@router.get("/quotes", response_model=QuoteBatch,
            summary="Giá khớp gần realtime của nhiều mã (cache ngắn, gộp 1 request)")
def market_quotes(
    symbols: str = Query(..., description="Danh sách mã, phân tách dấu phẩy: TPB,FPT"),
) -> QuoteBatch:
    codes = [s for s in (symbols or "").split(",") if s.strip()][:_MAX_SYMBOLS]
    return quote.fetch_quotes(codes)


@router.get("/highlights", response_model=MarketHighlights,
            summary="Ba khối điểm nhấn trang chủ: sự kiện sắp tới · tin mới · bảng điểm",
            description="Cả ba mảng đều có thể RỖNG khi nguồn không trả được — cố ý "
                        "để trống thay vì bịa số. Bảng điểm chấm theo mô hình 100 "
                        "điểm nên rất tốn request: chỉ tính cho vài mã vốn hóa lớn "
                        "nhất của rổ, đầy dần qua các lần gọi và cache 60 phút.")
def market_highlights(
    group: str = Query("VN30", description=f"Rổ cổ phiếu: {' · '.join(_GROUP_KEYS)}"),
    limit: int = Query(5, ge=1, le=10, description="Số dòng tối đa của MỖI khối"),
) -> MarketHighlights:
    key = group.upper().strip()
    if key not in _GROUP_KEYS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail=f"Rổ không hợp lệ. Chọn một trong: {', '.join(_GROUP_KEYS)}.")
    return highlights.fetch_highlights(key, limit)
