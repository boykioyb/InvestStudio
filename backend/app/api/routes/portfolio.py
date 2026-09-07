"""Danh mục tổng quan: đánh giá nhiều mã cùng lúc (chỉ giá + lãi/lỗ)."""
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import get_current_user
from app.core import ratelimit
from app.core.config import get_settings
from app.models.user import User
from app.schemas.stock import PortfolioRequest, PortfolioReview
from app.services import portfolio
from app.services.providers.base import ProviderError

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.post("/review", response_model=PortfolioReview,
             summary="Tổng quan danh mục: lãi/lỗ toàn bộ vị thế theo giá hiện tại")
def portfolio_review(payload: PortfolioRequest, request: Request,
                     user: User = Depends(get_current_user)) -> PortfolioReview:
    """Gộp các đợt mua của nhiều mã, lấy giá cả danh mục trong một request.

    KHÔNG cache: phụ thuộc các đợt mua người dùng vừa nhập. KHÔNG chấm điểm —
    điểm số/khuyến nghị từng mã xem ở endpoint `/stocks/{ticker}/position`.

    YÊU CẦU ĐĂNG NHẬP (H7): một request gọi được tới 100 mã, tức khuếch đại
    thành hàng trăm lượt crawl — nguồn chặn ở ~20 request/phút, bị chặn là CẢ
    trang chết. Mỗi lượt cũng tính vào hạn mức phân tích trong ngày.
    """
    ratelimit.enforce_daily(f"u:{user.id}", "analyze",
                            get_settings().member_analyze_daily, fail_open=True)
    try:
        return portfolio.review(payload)
    except ProviderError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
