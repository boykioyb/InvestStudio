"""Điểm khởi tạo FastAPI cho InvestStudio API."""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import (admin, auth, chat, market, notifications, portfolio,
                            screener, stocks, watchlist)
from app.core import ratelimit, settings_store
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


#  Ở môi trường thật KHÔNG phơi tài liệu API: /docs liệt kê sẵn mọi endpoint,
#  tham số và schema — bản đồ dò tìm miễn phí cho người muốn lạm dụng.
_IS_PROD = settings.env.lower() in ("prod", "production")

app = FastAPI(
    docs_url=None if _IS_PROD else "/docs",
    redoc_url=None if _IS_PROD else "/redoc",
    openapi_url=None if _IS_PROD else "/openapi.json",
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

#  Các đường KHÔNG tính vào giới hạn tần suất chung: health cho bộ giám sát,
#  SSE vì một luồng chỉ là MỘT request nhưng sống lâu.
_RATE_LIMIT_EXEMPT = ("/api/health",)


@app.middleware("http")
async def rate_limit_and_headers(request: Request, call_next):
    """Trần request/phút cho mỗi IP trên toàn bộ /api + header bảo mật.

    Trước đây chỉ đăng nhập/đăng ký mới bị đếm, còn mọi endpoint dữ liệu thì mở
    hoàn toàn — ai cũng quét được cả sàn ~1600 mã. Rào này FAIL-OPEN: Redis hỏng
    thì cho qua, vì mất trang còn tệ hơn chịu tải.
    """
    path = request.url.path
    if path.startswith("/api") and not path.startswith(_RATE_LIMIT_EXEMPT):
        try:
            ratelimit.enforce_window(request, "api", settings.api_rate_limit_per_minute, 60)
        except HTTPException as exc:
            #  Middleware nằm NGOÀI hệ thống xử lý ngoại lệ của FastAPI nên phải
            #  tự dựng phản hồi, không thể để HTTPException bay lên.
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code,
                                headers=exc.headers or {})

    #  Chế độ bảo trì: chặn API cho người dùng thường, /admin và đăng nhập vẫn
    #  mở để quản trị còn vào tắt cờ được (nếu không thì tự nhốt mình bên ngoài).
    if (path.startswith("/api") and settings_store.flag("maintenance_mode")
            and not path.startswith(("/api/health", "/api/admin", "/api/auth"))):
        return JSONResponse(
            {"detail": "Hệ thống đang bảo trì, vui lòng quay lại sau ít phút."},
            status_code=503)

    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Frame-Options", "DENY")
    if _IS_PROD:
        response.headers.setdefault("Strict-Transport-Security",
                                    "max-age=31536000; includeSubDomains")
    return response


app.include_router(stocks.router, prefix="/api")
app.include_router(screener.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(watchlist.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(market.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")
