"""Giới hạn tần suất & hạn mức bằng Redis.

Ba loại rào, KHÁC NHAU ở cách xử lý khi Redis hỏng:

| Loại | Ví dụ | Redis hỏng thì |
|---|---|---|
| Chống dò mật khẩu | `enforce(request, "login")` | **cho qua** — không được tự khóa cửa nhà mình |
| Giới hạn chung theo IP | `enforce_window(...)` | **cho qua** — thà chịu tải còn hơn sập trang |
| Hạn mức TIÊU HAO có hạn | `enforce_daily(...)` cho quota trợ lý | **CHẶN** (fail-closed) |

Vì sao hạn mức tiêu hao phải chặn: Gemini đang chạy bản miễn phí — quota ngày
hữu hạn và không mua thêm được. Redis chết mà vẫn cho gọi thoải mái thì vài phút
là sạch quota, và trợ lý im lặng với TẤT CẢ người dùng tới 0h hôm sau.
"""
from __future__ import annotations

import logging
import ipaddress
from datetime import date
from functools import lru_cache

from fastapi import HTTPException, Request, status

from app.core.config import get_settings

logger = logging.getLogger("app.ratelimit")


@lru_cache
def redis_client():
    import redis
    return redis.Redis.from_url(get_settings().rate_limit_redis_url,
                                socket_timeout=1, socket_connect_timeout=1)


def _client_ip(request: Request) -> str:
    """IP thật của client — CHỈ tin X-Forwarded-For khi đến từ proxy của mình.

    `X-Forwarded-For` là header do CLIENT gửi được: ai cũng tự ghi vào đó một IP
    bịa rồi vượt mọi rào đếm-theo-IP. Nên:

    1. Nếu người gọi trực tiếp KHÔNG nằm trong `trusted_proxies` → dùng luôn IP
       kết nối, bỏ qua header.
    2. Nếu có → lấy hop **từ CUỐI chuỗi** (phần do proxy của mình ghi thêm), chứ
       không lấy hop đầu như trước: hop đầu chính là phần client tự khai.
    """
    settings = get_settings()
    peer = request.client.host if request.client else "unknown"
    if not _is_trusted_proxy(peer, settings.trusted_proxies):
        return peer

    #  Proxy Nuxt GHI ĐÈ x-real-ip bằng địa chỉ socket thật (frontend/server/api/
    #  [...].ts) — ưu tiên dùng, vì nó không lẫn phần do client tự khai.
    if real_ip := request.headers.get("x-real-ip", "").strip():
        return real_ip

    chain = [part.strip() for part in
             request.headers.get("x-forwarded-for", "").split(",") if part.strip()]
    if not chain:
        return peer
    hops = max(1, settings.trusted_proxy_hops)
    return chain[-hops] if len(chain) >= hops else chain[0]


def _is_trusted_proxy(peer: str, trusted: list[str]) -> bool:
    """`peer` có phải proxy của mình không. Nhận IP đơn, dải CIDR, hoặc "*".

    Cần CIDR vì IP container Docker do mạng cấp động — không ghi cứng được. Dải
    mạng nội bộ của compose (VD 172.16.0.0/12) thì ổn định.
    """
    if not trusted:
        return False
    if "*" in trusted:
        return True
    try:
        addr = ipaddress.ip_address(peer)
    except ValueError:
        return False
    for entry in trusted:
        try:
            if addr in ipaddress.ip_network(entry, strict=False):
                return True
        except ValueError:
            continue
    return False


def ip_in_list(ip: str, entries: list[str]) -> bool:
    """IP có nằm trong danh sách (IP đơn / dải CIDR / "*") không."""
    return _is_trusted_proxy(ip, entries)


def enforce(request: Request, scope: str) -> None:
    """Đếm theo IP trong cửa sổ đăng nhập; quá ngưỡng → 429. Redis lỗi → cho qua."""
    settings = get_settings()
    enforce_window(request, scope, settings.login_max_attempts, settings.login_window_seconds)


def enforce_window(request: Request, scope: str, limit: int, window_seconds: int) -> None:
    """Trần `limit` request/`window_seconds` cho mỗi IP. Redis lỗi → FAIL-OPEN."""
    key = f"rl:{scope}:{_client_ip(request)}"
    try:
        client = redis_client()
        count = client.incr(key)
        if count == 1:
            client.expire(key, window_seconds)
        if count > limit:
            ttl = client.ttl(key)
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Quá nhiều lượt gọi. Vui lòng đợi {max(ttl, 1)} giây rồi thử lại.",
                headers={"Retry-After": str(max(ttl, 1))},
            )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - Redis trục trặc không được chặn cả trang
        logger.warning("Bỏ qua giới hạn tần suất vì Redis lỗi", extra={"scope": scope, "error": str(exc)})


def clear(request: Request, scope: str) -> None:
    """Xóa bộ đếm (gọi sau khi đăng nhập THÀNH CÔNG)."""
    try:
        redis_client().delete(f"rl:{scope}:{_client_ip(request)}")
    except Exception:  # noqa: BLE001
        pass


def _daily_key(scope: str, subject: str) -> str:
    return f"quota:{scope}:{subject}:{date.today().isoformat()}"


def used_today(scope: str, subject: str) -> int:
    """Số lượt đã dùng hôm nay (0 nếu chưa dùng hoặc Redis lỗi)."""
    try:
        raw = redis_client().get(_daily_key(scope, subject))
        return int(raw) if raw else 0
    except Exception:  # noqa: BLE001
        return 0


def enforce_daily(subject: str, scope: str, limit: int, *, fail_open: bool = False) -> None:
    """Hạn mức theo NGÀY cho một chủ thể (user id / IP). Vượt → 429.

    `fail_open=False` (mặc định): Redis lỗi → **từ chối** phục vụ. Dùng cho thứ
    tiêu hao có hạn (quota Gemini). `fail_open=True`: Redis lỗi → cho qua, dùng
    cho rào bảo vệ nguồn dữ liệu (thà chịu tải còn hơn cả trang ngừng chạy).
    """
    key = _daily_key(scope, subject)
    try:
        client = redis_client()
        count = client.incr(key)
        if count == 1:
            client.expire(key, 86400)
    except Exception as exc:  # noqa: BLE001
        if fail_open:
            logger.warning("Bỏ qua hạn mức vì Redis lỗi (fail-open)", extra={"scope": scope, "error": str(exc)})
            return
        logger.error("Từ chối vì Redis lỗi (fail-closed)", extra={"scope": scope, "error": str(exc)})
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hệ thống hạn mức tạm thời không sẵn sàng. Vui lòng thử lại sau.") from exc

    if count > limit:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Đã dùng hết {limit} lượt hôm nay. Vui lòng quay lại sau 0h.",
            headers={"X-Quota-Limit": str(limit), "X-Quota-Remaining": "0"},
        )


def enforce_daily_buckets(buckets: list[tuple[str, str, int]], *,
                          fail_open: bool = False) -> None:
    """Nhiều rổ cùng lúc — rổ nào chạm trần thì chặn cả request.

    Hai lượt: ĐỌC hết trước rồi mới TĂNG. Nếu vừa đọc vừa tăng thì một request
    bị rổ cuối từ chối vẫn kịp trừ hạn mức ở các rổ trước — người dùng mất lượt
    oan vì một câu hỏi chưa từng được trả lời.
    """
    for scope, subject, limit in buckets:
        if used_today(scope, subject) >= limit:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                detail=_bucket_message(scope, limit),
                headers={"X-Quota-Limit": str(limit), "X-Quota-Remaining": "0"})
    for scope, subject, limit in buckets:
        enforce_daily(subject, scope, limit, fail_open=fail_open)


def _bucket_message(scope: str, limit: int) -> str:
    """Nói đúng rổ nào chạm trần — người dùng thật cần biết vì sao bị chặn."""
    if scope.endswith(":device"):
        return (f"Thiết bị này đã dùng hết {limit} lượt hỏi hôm nay. "
                "Đổi tài khoản không tăng thêm lượt — vui lòng quay lại sau 0h.")
    if scope.endswith(":ip"):
        return (f"Mạng bạn đang dùng đã hết {limit} lượt hỏi hôm nay. "
                "Vui lòng quay lại sau 0h.")
    if scope.endswith(":net"):
        return "Khu vực mạng này đang có lượng truy cập bất thường. Vui lòng thử lại sau."
    return f"Đã dùng hết {limit} lượt hôm nay. Vui lòng quay lại sau 0h."


def remaining_daily(scope: str, subject: str, limit: int) -> int:
    """Số lượt còn lại hôm nay — để frontend hiện 'còn 3/5 lượt'."""
    return max(0, limit - used_today(scope, subject))


def client_ip(request: Request) -> str:
    """Bản công khai của `_client_ip` cho các route dùng lại."""
    return _client_ip(request)
