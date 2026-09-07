"""Đo mức tiêu thụ: gom theo REQUEST rồi ghi một dòng khi request kết thúc.

Vì sao dùng ContextVar: số token nằm sâu trong `rag/gemini.py` (nơi gọi API),
còn thứ cần ghi lại — ai hỏi, mã nào, mất bao lâu — chỉ có ở tầng route. Biến
ngữ cảnh cho phép tầng dưới cộng dồn mà không phải thay chữ ký của cả chuỗi hàm.

Hai đích đến:
- **Redis**: bộ đếm nhanh trong ngày → /admin đọc tức thì, không đụng cơ sở dữ liệu.
- **Postgres** (`usage_events`): một dòng cho mỗi việc ĐẮT, để còn truy vết.
"""
from __future__ import annotations

import sys
import time
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date

from sqlalchemy.orm import Session

from app.core.ratelimit import redis_client

_current: ContextVar[dict | None] = ContextVar("usage_current", default=None)


@contextmanager
def track():
    """Mở một phạm vi đo. Lồng nhau thì phạm vi ngoài cùng thắng."""
    token = _current.set({"calls": 0, "tokens_in": 0, "tokens_out": 0, "t0": time.monotonic()})
    try:
        yield
    finally:
        _current.reset(token)


def add_call(tokens_in: int = 0, tokens_out: int = 0) -> None:
    """Tầng gemini.py gọi sau MỖI request thật tới Google."""
    bucket = _current.get()
    if bucket is None:
        return
    bucket["calls"] += 1
    bucket["tokens_in"] += int(tokens_in or 0)
    bucket["tokens_out"] += int(tokens_out or 0)


def snapshot() -> dict:
    bucket = _current.get()
    if bucket is None:
        return {"calls": 0, "tokens_in": 0, "tokens_out": 0, "latency_ms": 0}
    return {
        "calls": bucket["calls"],
        "tokens_in": bucket["tokens_in"],
        "tokens_out": bucket["tokens_out"],
        "latency_ms": int((time.monotonic() - bucket["t0"]) * 1000),
    }


def _bump_redis(kind: str, user_id: int | None, ticker: str, data: dict, status: str) -> None:
    """Bộ đếm trong ngày (TTL 8 ngày để /admin còn vẽ được biểu đồ tuần)."""
    today = date.today().isoformat()
    try:
        client = redis_client()
        pipe = client.pipeline()
        pipe.hincrby(f"usage:{today}:{kind}", "count", 1)
        pipe.hincrby(f"usage:{today}:{kind}", "calls", data["calls"])
        pipe.hincrby(f"usage:{today}:{kind}", "tokens_in", data["tokens_in"])
        pipe.hincrby(f"usage:{today}:{kind}", "tokens_out", data["tokens_out"])
        if status != "ok":
            pipe.hincrby(f"usage:{today}:{kind}", "errors", 1)
        pipe.expire(f"usage:{today}:{kind}", 86400 * 8)
        if user_id:
            pipe.zincrby(f"usage:{today}:top:user", 1, str(user_id))
            pipe.expire(f"usage:{today}:top:user", 86400 * 8)
        if ticker:
            pipe.zincrby(f"usage:{today}:top:ticker", 1, ticker)
            pipe.expire(f"usage:{today}:top:ticker", 86400 * 8)
        pipe.execute()
    except Exception as exc:  # noqa: BLE001 - số liệu hỏng không được hỏng tính năng
        print(f"[usage] không ghi được bộ đếm: {exc}", file=sys.stderr)


def record(db: Session | None, kind: str, *, user_id: int | None = None, ip: str = "",
           fp_hash: str = "", ticker: str = "", status: str = "ok") -> None:
    """Chốt sổ một việc đắt: ghi Redis + (nếu có phiên DB) một dòng usage_events."""
    data = snapshot()
    _bump_redis(kind, user_id, ticker, data, status)
    if db is None:
        return
    from app.models.usage import UsageEvent
    try:
        db.add(UsageEvent(user_id=user_id, ip=ip[:45], fp_hash=fp_hash[:64], kind=kind,
                          ticker=ticker[:12], calls=data["calls"], tokens_in=data["tokens_in"],
                          tokens_out=data["tokens_out"], latency_ms=data["latency_ms"],
                          status=status))
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(f"[usage] không ghi được usage_events: {exc}", file=sys.stderr)


def today_counters() -> dict[str, dict[str, int]]:
    """Bộ đếm hôm nay theo từng loại — cho thẻ số ở trang Tổng quan."""
    today = date.today().isoformat()
    out: dict[str, dict[str, int]] = {}
    try:
        client = redis_client()
        for kind in ("chat", "analyze", "embed"):
            raw = client.hgetall(f"usage:{today}:{kind}") or {}
            out[kind] = {k.decode(): int(v) for k, v in raw.items()}
    except Exception as exc:  # noqa: BLE001
        print(f"[usage] không đọc được bộ đếm: {exc}", file=sys.stderr)
    return out


def top_today(what: str, limit: int = 20) -> list[tuple[str, int]]:
    """Xếp hạng hôm nay: `what` ∈ {"user", "ticker"}."""
    today = date.today().isoformat()
    try:
        rows = redis_client().zrevrange(f"usage:{today}:top:{what}", 0, limit - 1,
                                        withscores=True)
        return [(member.decode(), int(score)) for member, score in rows]
    except Exception:  # noqa: BLE001
        return []
