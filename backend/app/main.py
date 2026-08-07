"""Điểm khởi tạo FastAPI cho InvestStudio API."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import screener, stocks
from app.core.config import get_settings
from app.schemas.stock import HealthResponse

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "API phân tích cổ phiếu Việt Nam: crawl dữ liệu công khai → chấm điểm "
        "theo mô hình 100 điểm (14 tiêu chí / 4 nhóm). "
        "Toàn bộ logic chấm điểm nằm ở backend — frontend chỉ hiển thị. "
        "⚠️ Công cụ hỗ trợ tư duy, KHÔNG phải khuyến nghị đầu tư."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(stocks.router, prefix="/api")
app.include_router(screener.router, prefix="/api")


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")
