"""Danh mục tổng quan: đánh giá nhiều mã cùng lúc (chỉ giá + lãi/lỗ)."""
from fastapi import APIRouter, HTTPException, status

from app.schemas.stock import PortfolioRequest, PortfolioReview
from app.services import portfolio
from app.services.providers.base import ProviderError

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.post("/review", response_model=PortfolioReview,
             summary="Tổng quan danh mục: lãi/lỗ toàn bộ vị thế theo giá hiện tại")
def portfolio_review(payload: PortfolioRequest) -> PortfolioReview:
    """Gộp các đợt mua của nhiều mã, lấy giá cả danh mục trong một request.

    KHÔNG cache: phụ thuộc các đợt mua người dùng vừa nhập. KHÔNG chấm điểm —
    điểm số/khuyến nghị từng mã xem ở endpoint `/stocks/{ticker}/position`.
    """
    try:
        return portfolio.review(payload)
    except ProviderError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
