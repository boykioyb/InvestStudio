"""Dồn bộ đếm Redis vào bảng tổng hợp `usage_daily` (chạy nền theo lịch).

Redis là nơi ĐẾM (nhanh, chịu được mọi request), Postgres là nơi BÁO CÁO (bền,
vẽ được biểu đồ 30 ngày). Job này nối hai chỗ đó lại.

Chạy lặp lại nhiều lần trong ngày là an toàn: mỗi lần GHI ĐÈ dòng của hôm nay
bằng số hiện tại chứ không cộng dồn.
"""
from __future__ import annotations

import logging
import sys
from datetime import date

from app.core.ratelimit import redis_client
from app.db.session import SessionLocal


logger = logging.getLogger("app.usage_flush")

_KINDS = ("chat", "analyze", "embed")


def flush(day: date | None = None) -> dict[str, int]:
    from app.models.usage import UsageDaily

    day = day or date.today()
    key_day = day.isoformat()
    written = 0
    db = SessionLocal()
    try:
        client = redis_client()
        for kind in _KINDS:
            raw = client.hgetall(f"usage:{key_day}:{kind}") or {}
            if not raw:
                continue
            data = {k.decode(): int(v) for k, v in raw.items()}
            row = db.get(UsageDaily, (day, kind, 0))
            if row is None:
                row = UsageDaily(day=day, kind=kind, user_id=0)
                db.add(row)
            row.count = data.get("count", 0)
            row.calls = data.get("calls", 0)
            row.tokens_in = data.get("tokens_in", 0)
            row.tokens_out = data.get("tokens_out", 0)
            row.error_count = data.get("errors", 0)
            written += 1

        #  Dòng theo từng người (user_id > 0) để dựng bảng "ai dùng nhiều nhất".
        for member, score in client.zrevrange(f"usage:{key_day}:top:user", 0, 99,
                                              withscores=True):
            uid = int(member.decode()) if member.decode().isdigit() else 0
            if not uid:
                continue
            row = db.get(UsageDaily, (day, "chat", uid))
            if row is None:
                row = UsageDaily(day=day, kind="chat", user_id=uid)
                db.add(row)
            row.count = int(score)
            written += 1

        db.commit()
    except Exception as exc:  # noqa: BLE001 - job số liệu không được làm sập worker
        db.rollback()
        logger.error("Dồn bộ đếm thất bại", extra={"day": key_day, "error": str(exc)})
    finally:
        db.close()
    return {"rows": written, "day": key_day}
