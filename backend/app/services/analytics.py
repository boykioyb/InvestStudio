"""Ghi & đọc sự kiện sản phẩm (North Star Metric).

Hai hàm:

- `log_event(...)`  — chốt sổ MỘT sự kiện hành vi vào `product_events`. Tự mở/đóng
  session riêng: an toàn cả khi gọi từ generator SSE (nơi session request-scoped
  của FastAPI đã đóng). Nuốt mọi lỗi — đo số liệu KHÔNG được làm hỏng tính năng.

- `nsm_summary(...)` — tính 3 phương án North Star Metric trên một khoảng thời
  gian. Ở giai đoạn sớm (ít dữ liệu) tính trong Python cho đơn giản & chắc đúng;
  khi khối lượng lớn, chuyển sang SQL tương đương (đã ghi trong docs/scrum/nsm.md).

Danh tính người dùng để đếm "riêng biệt": ưu tiên user_id, khách rơi về fp_hash.
Sự kiện không có danh tính nào (cả hai rỗng) vẫn được ghi nhưng KHÔNG tính vào
"người dùng riêng biệt" vì không quy về ai được.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal

logger = logging.getLogger("app.analytics")

#  Các loại sự kiện hợp lệ. FE chỉ được ghi hai loại giao diện (xem routes/metrics.py);
#  analyze/assistant do máy chủ tự ghi để không giả mạo được.
EVENTS = ("analyze", "assistant", "why_open", "score_action")


def log_event(event: str, *, user_id: Optional[int] = None, fp_hash: str = "",
              ticker: str = "", ref: str = "", db: Optional[Session] = None) -> None:
    """Ghi một sự kiện hành vi. `db=None` → tự quản lý session (mặc định)."""
    if event not in EVENTS:
        return
    from app.models.analytics import ProductEvent

    own = db is None
    session = db or SessionLocal()
    try:
        session.add(ProductEvent(
            user_id=user_id, fp_hash=(fp_hash or "")[:64], event=event,
            ticker=(ticker or "")[:12], ref=(ref or "")[:48],
        ))
        session.commit()
    except Exception as exc:  # noqa: BLE001 - số liệu hỏng không được hỏng tính năng
        session.rollback()
        logger.warning("Không ghi được product_events", extra={"event": event, "error": str(exc)})
    finally:
        if own:
            session.close()


def _identity(user_id: Optional[int], fp_hash: str) -> str:
    """Khóa danh tính để dedup. Rỗng = không quy về ai (bỏ khi đếm user)."""
    if user_id:
        return f"u{user_id}"
    return fp_hash or ""


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 3) if denominator else 0.0


def nsm_summary(days: int = 7, db: Optional[Session] = None) -> dict:
    """Tính 3 phương án NSM trên `days` ngày gần nhất.

    Trả về dict gồm số liệu thô (để kiểm chứng) và tỉ lệ đã tính sẵn.
    """
    from app.models.analytics import ProductEvent

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    own = db is None
    session = db or SessionLocal()
    try:
        rows = session.execute(
            select(ProductEvent.event, ProductEvent.user_id,
                   ProductEvent.fp_hash, ProductEvent.ticker)
            .where(ProductEvent.at >= cutoff)
        ).all()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Không đọc được product_events", extra={"error": str(exc)})
        rows = []
    finally:
        if own:
            session.close()

    counts = {e: 0 for e in EVENTS}
    active: set[str] = set()                 # mọi danh tính có bất kỳ sự kiện nào
    analyzers: set[str] = set()              # đã phân tích (đã THẤY điểm)
    user_tickers: set[tuple[str, str]] = set()  # (danh tính, mã) → mã riêng biệt/user
    assistant_users: set[str] = set()
    why_users: set[str] = set()              # đã mở "vì sao điểm"
    action_users: set[str] = set()           # đã hành động sau khi xem điểm

    for event, user_id, fp_hash, ticker in rows:
        if event in counts:
            counts[event] += 1
        ident = _identity(user_id, fp_hash)
        if not ident:
            continue
        active.add(ident)
        if event == "analyze":
            analyzers.add(ident)
            if ticker:
                user_tickers.add((ident, ticker))
        elif event == "assistant":
            assistant_users.add(ident)
        elif event == "why_open":
            why_users.add(ident)
        elif event == "score_action":
            action_users.add(ident)

    why_and_saw = len(why_users & analyzers)
    why_then_acted = len(why_users & action_users)

    return {
        "window_days": days,
        "events": counts,
        "active_users": len(active),
        # NSM-A · Số mã user thực sự phân tích / tuần (trung bình mỗi người phân tích).
        "nsm_a_stocks_per_user": _ratio(len(user_tickers), len(analyzers)),
        "nsm_a_detail": {"distinct_user_ticker": len(user_tickers),
                         "analyzers": len(analyzers)},
        # NSM-B · Tỉ lệ user hoạt động có tương tác với trợ lý.
        "nsm_b_assistant_rate": _ratio(len(assistant_users), len(active)),
        "nsm_b_detail": {"assistant_users": len(assistant_users),
                         "active_users": len(active)},
        # NSM-C · Kiểm chứng lòng tin: % người xem điểm mở "vì sao", rồi % trong số
        #         đó có hành động. Đây là thước đo giả định nguy hiểm nhất.
        "nsm_c_why_open_rate": _ratio(why_and_saw, len(analyzers)),
        "nsm_c_act_after_why_rate": _ratio(why_then_acted, len(why_users)),
        "nsm_c_detail": {"why_users": len(why_users),
                         "why_users_who_saw_score": why_and_saw,
                         "why_users_who_acted": why_then_acted},
    }
