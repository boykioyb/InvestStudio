"""Log dạng JSON + gắn mã request, và Sentry (nếu có cấu hình).

Vì sao đổi khỏi `print()`: log một dòng chữ tự do thì con người đọc được nhưng
máy thì không. Khi có sự cố lúc 2h sáng, thứ cần là lọc được "tất cả request lỗi
của người dùng X trong 10 phút vừa rồi" — việc đó cần trường có cấu trúc.

Mỗi request được gắn `request_id`; mọi dòng log phát sinh trong request đó mang
cùng mã, nên ghép lại được thành một câu chuyện hoàn chỉnh.
"""
from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

from app.core.config import get_settings

#  Mã request hiện hành — middleware đặt, mọi log trong cùng request đọc lại.
request_id: ContextVar[str] = ContextVar("request_id", default="")

#  Các trường của LogRecord do stdlib tạo sẵn; phần còn lại là "extra" của mình.
_CHUAN = frozenset((
    "args", "asctime", "created", "exc_info", "exc_text", "filename", "funcName",
    "levelname", "levelno", "lineno", "module", "msecs", "message", "msg", "name",
    "pathname", "process", "processName", "relativeCreated", "stack_info",
    "taskName", "thread", "threadName",
))


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if rid := request_id.get():
            payload["request_id"] = rid
        if record.exc_info:
            payload["error"] = self.formatException(record.exc_info)
        #  Mọi `logger.info("...", extra={...})` được gộp thẳng vào JSON.
        payload.update({k: v for k, v in record.__dict__.items() if k not in _CHUAN})
        return json.dumps(payload, ensure_ascii=False, default=str)


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


def setup() -> None:
    """Gọi một lần lúc khởi động. Dev thì để log chữ thường cho dễ đọc."""
    settings = get_settings()
    is_prod = settings.env.lower() in ("prod", "production")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if is_prod
                         else logging.Formatter("%(levelname)s %(name)s: %(message)s"))

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)

    #  httpx ghi INFO cho MỌI lời gọi nguồn dữ liệu — ở prod thành hàng nghìn
    #  dòng JSON vô nghĩa mỗi ngày, lấp mất dòng thật sự cần đọc.
    logging.getLogger("httpx").setLevel(logging.WARNING)

    #  uvicorn tự cắm handler riêng → gỡ ra để mọi thứ đi qua một đường duy nhất.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True

    _setup_sentry(settings)


def _setup_sentry(settings) -> None:
    """Bật Sentry nếu có DSN. Không có thì im lặng bỏ qua — không phải ai cũng cần."""
    dsn = settings.sentry_dsn
    if not dsn:
        return
    try:
        import sentry_sdk
    except ImportError:
        logging.getLogger("app").warning("Có APP_SENTRY_DSN nhưng chưa cài sentry-sdk")
        return
    sentry_sdk.init(
        dsn=dsn,
        environment=settings.env,
        release=settings.version,
        #  Lấy mẫu vết chạy ở mức thấp: đây là công cụ nhỏ, không cần đo mọi request.
        traces_sample_rate=settings.sentry_traces_sample_rate,
        #  KHÔNG gửi kèm dữ liệu cá nhân (nội dung câu hỏi, email) sang bên thứ ba.
        send_default_pii=False,
    )
    logging.getLogger("app").info("Đã bật Sentry", extra={"environment": settings.env})
