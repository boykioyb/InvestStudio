"""Ngân sách Gemini: đếm REQUEST THẬT, giới hạn đồng thời, hạ cấp mềm.

Vì sao cần cả file này khi Gemini đang miễn phí: **không có hóa đơn không có
nghĩa là không có thiệt hại**. Bản miễn phí giới hạn cả số request/phút (RPM)
lẫn số request/ngày (RPD), và KHÔNG mua thêm được — ai đó đốt sạch quota lúc 9h
sáng thì trợ lý im lặng với mọi người tới 0h hôm sau.

Ba việc ở đây:

1. **Đếm request thật, không đếm "lượt hỏi".** Một lượt hỏi của agent bắn 3–7
   request (1 nhúng + tối đa `rag_agent_max_steps` vòng gọi tool + 1 lần chốt).
   Vì vậy bộ đếm nằm ở tầng này — nơi MỌI lệnh gọi Gemini đi qua — chứ không
   nằm ở tầng route.
2. **Giới hạn đồng thời.** ~10–15 RPM mà một câu hỏi bắn 3–7 request liên tiếp
   trong ~10 giây → chỉ 2–3 người hỏi cùng lúc là Google trả 429. Thà xếp hàng
   rồi trả lời chậm còn hơn báo lỗi.
3. **Hạ cấp mềm.** 70% quota → tắt agent, lui về RAG một nhịp (1 request thay
   vì 3–7). 90% → chỉ ai đã hỏi trong ngày mới được hỏi tiếp.

FAIL-CLOSED: Redis hỏng thì KHÔNG gọi Gemini. Thà báo bận vài phút còn hơn mất
sạch quota ngày mà không ai biết.

⚠️ Lệch múi giờ đã biết: bộ đếm này reset lúc 0h giờ Việt Nam, còn quota của
Google reset theo giờ Thái Bình Dương. Vì thế `gemini_daily_call_cap` nên đặt
THẤP HƠN quota thật (chừa biên + chừa phần cho job nền), đừng đặt sát trần.
"""
from __future__ import annotations

import sys
import time
from contextlib import contextmanager
from datetime import date

from app.core import settings_store
from app.core.config import get_settings
from app.core.ratelimit import redis_client


def _cap() -> int:
    """Trần request/ngày — ưu tiên giá trị chỉnh trong /admin (settings_store)."""
    return settings_store.quota("gemini_daily_call_cap") or get_settings().gemini_daily_call_cap


def _max_concurrent() -> int:
    return (settings_store.quota("gemini_max_concurrent")
            or get_settings().gemini_max_concurrent)

#  Số request Gemini ĐANG chạy (mọi tiến trình web + worker dùng chung khóa này).
_INFLIGHT_KEY = "gemini:inflight"
#  Hạn sống của khóa đồng thời: nếu tiến trình chết giữa chừng mà không kịp trả
#  chỗ, khóa tự hết hạn thay vì kẹt vĩnh viễn.
_INFLIGHT_TTL = 180


class BudgetError(RuntimeError):
    """Không gọi được Gemini vì hạn mức/hàng đợi — KHÔNG phải lỗi của Google."""


def _day_key() -> str:
    return f"gemini:calls:{date.today().isoformat()}"


def used_today() -> int:
    """Số request Gemini đã dùng hôm nay. Redis lỗi → coi như đã cạn (bảo thủ)."""
    try:
        raw = redis_client().get(_day_key())
        return int(raw) if raw else 0
    except Exception as exc:  # noqa: BLE001
        print(f"[budget] không đọc được bộ đếm: {exc}", file=sys.stderr)
        return _cap()


def usage_ratio() -> float:
    """Tỷ lệ quota ngày đã dùng (0.0 → 1.0+)."""
    cap = max(1, _cap())
    return used_today() / cap


def should_use_agent() -> bool:
    """Còn dưới ngưỡng hạ cấp thì cho chạy agent (đắt gấp ~4 lần RAG một nhịp)."""
    return usage_ratio() < get_settings().gemini_degrade_at


def new_questions_blocked() -> bool:
    """Trên ngưỡng này chỉ phục vụ người ĐÃ hỏi trong ngày, không nhận người mới."""
    return usage_ratio() >= get_settings().gemini_block_new_at


def status_snapshot() -> dict:
    """Tình trạng ngân sách — cho /admin và cho thông báo gửi người dùng."""
    settings = get_settings()
    used = used_today()
    cap = _cap()
    ratio = used / max(1, cap)
    level = "ok" if ratio < settings.gemini_degrade_at else (
        "saving" if ratio < settings.gemini_block_new_at else "exhausted")
    return {"used": used, "cap": cap, "ratio": round(ratio, 3), "level": level,
            "agent": level == "ok"}


@contextmanager
def slot():
    """Xin một suất gọi Gemini: tính vào quota ngày + chiếm một chỗ đồng thời.

    Dùng bọc quanh TỪNG lệnh gọi API (mỗi vòng agent là một lệnh gọi riêng).
    Ném `BudgetError` khi hết quota ngày, khi Redis hỏng, hoặc khi chờ quá lâu.
    """
    settings = get_settings()
    try:
        client = redis_client()
        used = client.incr(_day_key())
        if used == 1:
            client.expire(_day_key(), 86400)
    except Exception as exc:  # noqa: BLE001 - FAIL-CLOSED, xem docstring đầu file
        raise BudgetError("Hệ thống hạn mức tạm thời không sẵn sàng.") from exc

    if used > _cap():
        raise BudgetError(
            "Trợ lý đã dùng hết hạn mức chung của hôm nay. Vui lòng quay lại sau 0h.")

    #  Xếp hàng để không chạm trần request/phút của Google.
    deadline = time.monotonic() + settings.gemini_slot_wait_seconds
    acquired = False
    while True:
        try:
            inflight = client.incr(_INFLIGHT_KEY)
            client.expire(_INFLIGHT_KEY, _INFLIGHT_TTL)
            if inflight <= _max_concurrent():
                acquired = True
                break
            client.decr(_INFLIGHT_KEY)
        except Exception as exc:  # noqa: BLE001
            raise BudgetError("Hệ thống hạn mức tạm thời không sẵn sàng.") from exc
        if time.monotonic() >= deadline:
            raise BudgetError(
                "Trợ lý đang bận trả lời người khác. Vui lòng thử lại sau ít giây.")
        time.sleep(0.4)

    try:
        yield
    finally:
        if acquired:
            try:
                client.decr(_INFLIGHT_KEY)
            except Exception:  # noqa: BLE001 - khóa có TTL nên tự nhả nếu lỡ trượt
                pass


def reset_inflight() -> None:
    """Nhả cứng bộ đếm đồng thời (dùng khi vận hành thấy kẹt)."""
    try:
        redis_client().delete(_INFLIGHT_KEY)
    except Exception:  # noqa: BLE001
        pass
