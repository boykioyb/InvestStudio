"""Điểm khởi tạo FastAPI cho InvestStudio API."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, chat, screener, stocks, watchlist
from app.core.config import get_settings
from app.db.session import init_db
from app.schemas.stock import HealthResponse

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    #  Tạo extension pgvector + bảng nếu chưa có. Chạy đúng một lần lúc khởi động.
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "API phân tích cổ phiếu Việt Nam: crawl dữ liệu công khai → chấm điểm "
        "theo mô hình 100 điểm (14 tiêu chí / 4 nhóm). "
        "Toàn bộ logic chấm điểm nằm ở backend — frontend chỉ hiển thị. "
        "Có tài khoản người dùng (mã yêu thích, theo dõi nhanh) và trợ lý RAG. "
        "⚠️ Công cụ hỗ trợ tư duy, KHÔNG phải khuyến nghị đầu tư."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    #  Bật credentials để cookie đăng nhập (httpOnly) đi kèm request khi gọi
    #  THẲNG backend từ origin khác. Dùng cùng origin qua proxy Nuxt thì không
    #  đụng tới CORS, nhưng khai báo đúng để trường hợp gọi trực tiếp vẫn chạy.
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(stocks.router, prefix="/api")
app.include_router(screener.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(watchlist.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")
