"""Hạn mức hiệu lực của một tài khoản — ba tầng, giải ở MỘT chỗ.

Vì sao cần tầng: một con số chung (`rag_daily_quota`) không đủ khi vừa có người
dùng thử, vừa có khách trả tiền. Nâng con số chung cho cả hệ thống chỉ để ưu ái
một người là cách chắc chắn nhất để đốt sạch hạn mức Gemini miễn phí.

Thứ tự ưu tiên:

1. `users.chat_daily_quota` / `users.analyze_daily_quota` — riêng người.
   **NULL = chưa đặt** (khác hẳn 0 = chặn sạch) → rơi xuống tầng dưới.
2. `plan_<hạng>_<loại>_daily` — theo hạng tài khoản (`users.plan`).
   **Trống = chưa đặt** → rơi tiếp. Cố ý để trống được: nếu bắt buộc phải có giá
   trị thì ô "Lượt hỏi trợ lý / người / ngày" trong /admin thành công tắc chết —
   đặt số mà không ai thấy đổi, đúng loại bẫy khó lần ra.
3. Mức chung toàn hệ thống (`rag_daily_quota` / `member_analyze_daily`).

Mọi nơi tiêu hạn mức CỦA MỘT TÀI KHOẢN đều phải đi qua `effective()`; rải công
thức ra nhiều route là cách để chúng lệch nhau.
"""
from __future__ import annotations

from typing import Any

#  Hạng tài khoản. Thêm hạng mới = thêm ĐÚNG một dòng ở đây — khóa cấu hình
#  tương ứng trong /admin tự sinh theo (xem app/core/settings_store.py).
PLANS: tuple[str, ...] = ("free", "vip")
PLAN_LABEL: dict[str, str] = {"free": "Thường", "vip": "VIP"}

#  Loại hạn mức → khóa cấu hình chung, và nhãn cho người đọc.
KIND_LABEL: dict[str, str] = {"chat": "lượt hỏi trợ lý", "analyze": "lượt phân tích"}
GLOBAL_KEY: dict[str, str] = {"chat": "rag_daily_quota", "analyze": "member_analyze_daily"}

KINDS: tuple[str, ...] = tuple(KIND_LABEL)


def plan_of(user: Any) -> str:
    """Hạng của tài khoản, đã kiểm hợp lệ. Hạng lạ (dữ liệu cũ) coi như hạng đầu."""
    plan = getattr(user, "plan", None)
    return plan if plan in PLANS else PLANS[0]


def tier_key(plan: str, kind: str) -> str:
    """Khóa cấu hình của một hạng — sinh ở đây để settings_store khỏi lệch tên."""
    return f"plan_{plan}_{kind}_daily"


def effective(user: Any, kind: str) -> int:
    """Hạn mức/ngày có hiệu lực với `user` cho `kind` ('chat' | 'analyze')."""
    if kind not in GLOBAL_KEY:
        raise KeyError(kind)

    #  Nhập BÊN TRONG hàm: settings_store nhập PLANS từ module này ở cấp module,
    #  nên nhập vòng ở cấp module sẽ hỏng.
    from app.core import settings_store

    #  Tầng 1 — riêng người. `is not None` chứ không phải `or`: 0 là giá trị
    #  THẬT ("tắt trợ lý cho riêng người này"), không phải "chưa đặt".
    override = getattr(user, f"{kind}_daily_quota", None)
    if override is not None:
        return max(0, int(override))

    #  Tầng 2 — theo hạng. `get()` chứ KHÔNG phải `quota()`: `quota()` trả 0 khi
    #  chưa đặt, mà 0 trong ratelimit.enforce_daily nghĩa là chặn sạch.
    tier = settings_store.get(tier_key(plan_of(user), kind))
    if tier is not None:
        return max(0, int(tier))

    #  Tầng 3 — mức chung, luôn có giá trị (config.py giữ mặc định).
    return settings_store.quota(GLOBAL_KEY[kind])
