"""Giới hạn tần suất bằng Redis — chống dò mật khẩu (brute force).

Đếm theo IP trong một cửa sổ thời gian; quá ngưỡng → 429. Đăng nhập THÀNH CÔNG
thì xóa bộ đếm để người dùng thật không bị phạt oan. Redis lỗi → FAIL-OPEN (cho
qua): giới hạn tần suất là phòng thủ bổ sung, không được tự khóa cả hệ thống.
"""
from __future__ import annotations

import sys
from functools import lru_cache

from fastapi import HTTPException, Request, status

from app.core.config import get_settings


@lru_cache
def _redis():
    import redis
    return redis.Redis.from_url(get_settings().rate_limit_redis_url,
                                socket_timeout=1, socket_connect_timeout=1)


def _client_ip(request: Request) -> str:
    #  Qua proxy Nuxt/LB → IP thật nằm ở X-Forwarded-For (hop đầu tiên).
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce(request: Request, scope: str) -> None:
    """Tăng bộ đếm theo IP; quá ngưỡng → 429. Redis lỗi thì bỏ qua (fail-open)."""
    settings = get_settings()
    key = f"rl:{scope}:{_client_ip(request)}"
    try:
        client = _redis()
        count = client.incr(key)
        if count == 1:
            client.expire(key, settings.login_window_seconds)
        if count > settings.login_max_attempts:
            ttl = client.ttl(key)
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Quá nhiều lần thử. Vui lòng đợi {max(ttl, 1)} giây rồi thử lại.",
            )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - Redis trục trặc không được chặn đăng nhập
        print(f"[ratelimit] bỏ qua vì Redis lỗi: {exc}", file=sys.stderr)


def clear(request: Request, scope: str) -> None:
    """Xóa bộ đếm (gọi sau khi đăng nhập THÀNH CÔNG)."""
    try:
        _redis().delete(f"rl:{scope}:{_client_ip(request)}")
    except Exception:  # noqa: BLE001
        pass


def enforce_daily(subject: str, scope: str, limit: int) -> None:
    """Quota theo NGÀY cho một chủ thể (VD user id). Vượt → 429. Redis lỗi → cho qua."""
    from datetime import date

    key = f"quota:{scope}:{subject}:{date.today().isoformat()}"
    try:
        client = _redis()
        count = client.incr(key)
        if count == 1:
            client.expire(key, 86400)
        if count > limit:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Đã dùng hết {limit} lượt hỏi trợ lý hôm nay. Vui lòng thử lại ngày mai.")
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - Redis lỗi không được chặn tính năng
        print(f"[quota] bỏ qua vì Redis lỗi: {exc}", file=sys.stderr)
