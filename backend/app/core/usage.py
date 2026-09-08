"""Đo mức tiêu thụ: gom theo REQUEST rồi ghi một dòng khi request kết thúc.

Vì sao dùng ContextVar: số token nằm sâu trong `rag/gemini.py` (nơi gọi API),
còn thứ cần ghi lại — ai hỏi, mã nào, mất bao lâu — chỉ có ở tầng route. Biến
ngữ cảnh cho phép tầng dưới cộng dồn mà không phải thay chữ ký của cả chuỗi hàm.

Hai đích đến:
- **Redis**: bộ đếm nhanh trong ngày → /admin đọc tức thì, không đụng cơ sở dữ liệu.
- **Postgres** (`usage_events`): một dòng cho mỗi việc ĐẮT, để còn truy vết.
"""
from __future__ import annotations

import logging
import sys
import time
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date

from sqlalchemy.orm import Session

from app.core.ratelimit import redis_client


logger = logging.getLogger("app.usage")

class Tracker:
    """Bộ cộng dồn của MỘT lượt việc. Là đối tượng thường, không phải ContextVar.

    Vì sao cần tách ra: luồng SSE được Starlette chạy bằng cách gọi `next()`
    trên generator qua threadpool — mỗi bước có thể rơi vào một ngữ cảnh khác.
    ContextVar đặt bên trong generator sẽ mất giá trị giữa các bước, và lệnh
    reset còn ném `ValueError: Token was created in a different Context`.
    Đối tượng này thì đi theo generator, không phụ thuộc ngữ cảnh nào.
    """

    __slots__ = ("calls", "tokens_in", "tokens_out", "t0")

    def __init__(self) -> None:
        self.calls = 0
        self.tokens_in = 0
        self.tokens_out = 0
        self.t0 = time.monotonic()

    def add(self, tokens_in: int = 0, tokens_out: int = 0) -> None:
        self.calls += 1
        self.tokens_in += int(tokens_in or 0)
        self.tokens_out += int(tokens_out or 0)

    def snapshot(self) -> dict:
        return {"calls": self.calls, "tokens_in": self.tokens_in,
                "tokens_out": self.tokens_out,
                "latency_ms": int((time.monotonic() - self.t0) * 1000)}


_current: ContextVar[Tracker | None] = ContextVar("usage_current", default=None)


@contextmanager
def bind(tracker: Tracker):
    """Gắn `tracker` vào ngữ cảnh HIỆN TẠI trong đúng một đoạn đồng bộ.

    Dùng cho luồng SSE: bọc quanh TỪNG bước `next()` để set và reset luôn nằm
    trong cùng một ngữ cảnh, còn số liệu vẫn cộng dồn trên chính đối tượng.
    """
    token = _current.set(tracker)
    try:
        yield tracker
    finally:
        _current.reset(token)


@contextmanager
def track():
    """Mở phạm vi đo cho một lượt việc ĐỒNG BỘ (không có yield ở giữa)."""
    with bind(Tracker()) as tracker:
        yield tracker


def add_call(tokens_in: int = 0, tokens_out: int = 0) -> None:
    """Tầng gemini.py gọi sau MỖI request thật tới Google."""
    tracker = _current.get()
    if tracker is not None:
        tracker.add(tokens_in, tokens_out)


def snapshot(tracker: Tracker | None = None) -> dict:
    tracker = tracker or _current.get()
    if tracker is None:
        return {"calls": 0, "tokens_in": 0, "tokens_out": 0, "latency_ms": 0}
    return tracker.snapshot()


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
        logger.warning("Không ghi được bộ đếm sử dụng", extra={"kind": kind, "error": str(exc)})


def record(db: Session | None, kind: str, *, user_id: int | None = None, ip: str = "",
           fp_hash: str = "", ticker: str = "", status: str = "ok",
           tracker: Tracker | None = None) -> None:
    """Chốt sổ một việc đắt: ghi Redis + (nếu có phiên DB) một dòng usage_events."""
    data = snapshot(tracker)
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
        logger.warning("Không ghi được usage_events", extra={"kind": kind, "error": str(exc)})


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
        logger.warning("Không đọc được bộ đếm sử dụng", extra={"error": str(exc)})
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
