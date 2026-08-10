"""Điểm khởi tạo FastAPI cho InvestStudio API."""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, chat, screener, stocks, watchlist
from app.core.config import DEV_JWT_SECRET, get_settings
from app.db.session import init_db
from app.schemas.stock import HealthResponse

settings = get_settings()


def _check_secrets() -> None:
    """Không cho phép chạy môi trường thật bằng JWT secret mặc định.

    Nếu để nguyên placeholder, ai đọc mã nguồn (đã công khai) cũng ký được token
    giả với `sub` bất kỳ → chiếm mọi tài khoản. Ràng vào cookie_secure: khi đã bật
    HTTPS (dấu hiệu môi trường thật) thì BẮT BUỘC đặt secret riêng, nếu không app
    từ chối khởi động.
    """
    if settings.jwt_secret == DEV_JWT_SECRET:
        if settings.cookie_secure:
            raise RuntimeError(
                "APP_JWT_SECRET vẫn là giá trị mặc định trong khi APP_COOKIE_SECURE=true. "
                "Hãy đặt APP_JWT_SECRET là chuỗi ngẫu nhiên ≥ 32 ký tự trước khi lên môi trường thật."
            )
        print("⚠️  Đang dùng JWT secret MẶC ĐỊNH (chỉ hợp cho dev). "
              "Đặt APP_JWT_SECRET trước khi triển khai thật.", file=sys.stderr)


@asynccontextmanager
async def lifespan(_: FastAPI):
    #  Tạo extension pgvector + bảng nếu chưa có. Chạy đúng một lần lúc khởi động.
    _check_secrets()
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
