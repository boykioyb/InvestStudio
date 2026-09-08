"""Điểm khởi tạo FastAPI cho Phân Tích Mã API."""
from __future__ import annotations

import logging
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import (admin, admin_ops, auth, chat, market, notifications,
                            portfolio, screener, stocks, watchlist)
from app.core import applog, ratelimit, settings_store
from app.core.config import DEV_JWT_SECRET, get_settings
from app.db.session import init_db
from app.schemas.stock import DependencyHealth, HealthResponse

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


logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_: FastAPI):
    #  Tạo extension pgvector + bảng nếu chưa có. Chạy đúng một lần lúc khởi động.
    applog.setup()
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

def _ghi_log(request: Request, status_code: int, started: float) -> None:
    """Một dòng cho mỗi request API. Lỗi 5xx lên mức error để lọc riêng được."""
    muc = logging.ERROR if status_code >= 500 else (
        logging.WARNING if status_code >= 400 else logging.INFO)
    logger.log(muc, "%s %s %s", request.method, request.url.path, status_code, extra={
        "method": request.method,
        "path": request.url.path,
        "status": status_code,
        "duration_ms": int((time.monotonic() - started) * 1000),
        "ip": ratelimit.client_ip(request),
    })


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
    #  Mã request: gắn vào mọi dòng log phát sinh bên trong, và trả về header để
    #  người dùng báo lỗi kèm mã là tra được đúng vệt log.
    rid = request.headers.get("x-request-id") or applog.new_request_id()
    applog.request_id.set(rid)
    started = time.monotonic()

    path = request.url.path
    if path.startswith("/api") and not path.startswith(_RATE_LIMIT_EXEMPT):
        try:
            ratelimit.enforce_window(request, "api", settings.api_rate_limit_per_minute, 60)
        except HTTPException as exc:
            #  Middleware nằm NGOÀI hệ thống xử lý ngoại lệ của FastAPI nên phải
            #  tự dựng phản hồi, không thể để HTTPException bay lên.
            _ghi_log(request, exc.status_code, started)
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code,
                                headers={**(exc.headers or {}), "X-Request-Id": rid})

    #  Chế độ bảo trì: chặn API cho người dùng thường, /admin và đăng nhập vẫn
    #  mở để quản trị còn vào tắt cờ được (nếu không thì tự nhốt mình bên ngoài).
    if (path.startswith("/api") and settings_store.flag("maintenance_mode")
            and not path.startswith(("/api/health", "/api/admin", "/api/auth"))):
        _ghi_log(request, 503, started)
        return JSONResponse(
            {"detail": "Hệ thống đang bảo trì, vui lòng quay lại sau ít phút."},
            status_code=503, headers={"X-Request-Id": rid})

    response = await call_next(request)
    if path.startswith("/api"):
        _ghi_log(request, response.status_code, started)
    response.headers["X-Request-Id"] = rid
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
app.include_router(admin_ops.router, prefix="/api")


def _check(name: str, probe, *, required: bool) -> tuple[DependencyHealth, bool]:
    """Chạy một phép thử, đo thời gian, KHÔNG để lỗi lọt ra ngoài.

    Trả kèm cờ "có làm hỏng trạng thái chung không" — Gemini chưa cấu hình thì
    trợ lý tắt, nhưng phần phân tích cổ phiếu vẫn chạy, nên không thể coi là sập.
    """
    started = time.monotonic()
    try:
        detail = probe() or ""
        took = int((time.monotonic() - started) * 1000)
        return DependencyHealth(name=name, ok=True, detail=detail, latency_ms=took), False
    except Exception as exc:  # noqa: BLE001 - health check không được tự ném lỗi
        took = int((time.monotonic() - started) * 1000)
        return DependencyHealth(name=name, ok=False, detail=str(exc)[:200],
                                latency_ms=took), required


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Kiểm tra sống CÓ THỰC CHẤT: chạm thật vào DB, Redis và cấu hình Gemini.

    Bản cũ luôn trả "ok" kể cả khi cơ sở dữ liệu đã sập — bộ giám sát thấy xanh
    trong khi người dùng không đăng nhập được. Sập DB/Redis → 503 để bộ cân bằng
    tải rút container này ra khỏi vòng phục vụ.
    """
    from sqlalchemy import text

    from app.core.budget import status_snapshot
    from app.core.ratelimit import redis_client
    from app.db.session import engine

    def _db() -> str:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "kết nối được"

    def _redis() -> str:
        redis_client().ping()
        return "kết nối được"

    def _gemini() -> str:
        if not settings.gemini_api_key:
            raise RuntimeError("chưa cấu hình APP_GEMINI_API_KEY — trợ lý sẽ không chạy")
        snap = status_snapshot()
        return f"đã dùng {snap['used']}/{snap['cap']} request hôm nay ({snap['level']})"

    checks, hong = [], False
    for name, probe, required in (("database", _db, True), ("redis", _redis, True),
                                  ("gemini", _gemini, False)):
        result, lam_hong = _check(name, probe, required=required)
        checks.append(result)
        hong = hong or lam_hong

    status_text = "ok" if all(c.ok for c in checks) else "degraded"
    body = HealthResponse(status=status_text, version=settings.version, checks=checks)
    if hong:
        #  Thành phần BẮT BUỘC hỏng → 503, không phải 200 kèm chữ "degraded":
        #  bộ giám sát nào cũng hiểu mã trạng thái, không phải cái nào cũng đọc thân.
        return JSONResponse(body.model_dump(mode="json"), status_code=503)
    return body
