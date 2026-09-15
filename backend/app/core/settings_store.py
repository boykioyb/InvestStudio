"""Cấu hình CHẠY được đổi trong /admin — "cần gạt khẩn cấp".

Vì sao không dùng biến môi trường: khi đang bị lạm dùng lúc 2h sáng, thứ cứu
được là một cái công tắc bấm phát ăn ngay, không phải một lần deploy lại.

Nguồn giá trị theo thứ tự: bảng `app_settings` → `Settings` trong config.py.
Đọc qua cache 30 giây nên bật/tắt có hiệu lực trong vòng nửa phút mà không bắt
mỗi request phải truy vấn cơ sở dữ liệu.
"""
from __future__ import annotations

import logging
import sys
import time
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.plans import KIND_LABEL, KINDS, PLAN_LABEL, PLANS, tier_key
from app.db.session import SessionLocal

#  Khai báo các khóa cho phép chỉnh + giá trị mặc định lấy từ đâu.
#  `None` nghĩa là mặc định nằm ở config.py cùng tên khóa.
SCHEMA: dict[str, dict[str, Any]] = {
    "assistant_enabled": {"type": "bool", "default": True,
                          "label": "Bật trợ lý", "group": "Cần gạt khẩn cấp"},
    "registration_open": {"type": "bool", "default": True,
                          "label": "Mở đăng ký tài khoản mới", "group": "Cần gạt khẩn cấp"},
    "refresh_enabled": {"type": "bool", "default": True,
                        "label": "Cho phép ép crawl lại (refresh)", "group": "Cần gạt khẩn cấp"},
    "maintenance_mode": {"type": "bool", "default": False,
                         "label": "Chế độ bảo trì (chỉ quản trị vào được)",
                         "group": "Cần gạt khẩn cấp"},
    "rag_daily_quota": {"type": "int", "default": None,
                        "label": "Lượt hỏi trợ lý / người / ngày", "group": "Hạn mức"},
    "chat_daily_per_device": {"type": "int", "default": None,
                              "label": "Lượt hỏi / thiết bị / ngày", "group": "Hạn mức"},
    "chat_daily_per_ip": {"type": "int", "default": None,
                          "label": "Lượt hỏi / IP / ngày", "group": "Hạn mức"},
    "guest_analyze_daily": {"type": "int", "default": None,
                            "label": "Lượt phân tích / khách / ngày", "group": "Hạn mức"},
    "member_analyze_daily": {"type": "int", "default": None,
                             "label": "Lượt phân tích / thành viên / ngày", "group": "Hạn mức"},
    "pow_after_accounts": {"type": "int", "default": None,
                           "label": "Bắt giải đố từ tài khoản thứ N trên một thiết bị",
                           "group": "Hạn mức"},
    "max_accounts_per_device": {"type": "int", "default": None,
                                "label": "Trần số tài khoản trên một thiết bị",
                                "group": "Hạn mức"},
    "gemini_daily_call_cap": {"type": "int", "default": None,
                              "label": "Trần request Gemini / ngày (đọc từ AI Studio)",
                              "group": "Gemini"},
    "gemini_max_concurrent": {"type": "int", "default": None,
                              "label": "Số câu hỏi gọi Gemini cùng lúc", "group": "Gemini"},
    "rag_agent_max_steps": {"type": "int", "default": None,
                            "label": "Số vòng gọi công cụ tối đa mỗi câu", "group": "Gemini"},
}


def _khoa_theo_hang() -> dict[str, dict[str, Any]]:
    """Khóa hạn mức theo HẠNG — sinh từ app/core/plans.py.

    Thêm hạng mới trong PLANS là khóa cấu hình xuất hiện luôn trong /admin,
    không phải sửa file này. `default: None` = CHƯA ĐẶT, nên ô để trống được và
    hạn mức rơi xuống mức chung — xem app/core/plans.effective().
    """
    out: dict[str, dict[str, Any]] = {}
    for hang in PLANS:
        for loai in KINDS:
            out[tier_key(hang, loai)] = {
                "type": "int", "default": None,
                "label": (f"Hạng {PLAN_LABEL[hang]} — {KIND_LABEL[loai]} / ngày "
                          "(trống = dùng mức chung)"),
                "group": "Hạn mức",
            }
    return out


SCHEMA.update(_khoa_theo_hang())


logger = logging.getLogger("app.settings")

_CACHE: dict[str, Any] = {}
_CACHE_AT: float = 0.0
_TTL = 30.0


def _load() -> dict[str, Any]:
    """Đọc toàn bộ bảng cấu hình (có cache). Lỗi DB → dùng cache cũ/mặc định."""
    global _CACHE, _CACHE_AT
    if _CACHE_AT and time.monotonic() - _CACHE_AT < _TTL:
        return _CACHE
    from app.models.admin import AppSetting
    db: Session = SessionLocal()
    try:
        rows = db.query(AppSetting).all()
        _CACHE = {row.key: (row.value or {}).get("v") for row in rows}
        _CACHE_AT = time.monotonic()
    except Exception as exc:  # noqa: BLE001 - cấu hình hỏng không được làm sập trang
        logger.warning("Đọc cấu hình thất bại, dùng mặc định", extra={"error": str(exc)})
    finally:
        db.close()
    return _CACHE


def invalidate() -> None:
    """Xóa cache — gọi ngay sau khi ghi để thao tác trong /admin thấy hiệu lực liền."""
    global _CACHE_AT
    _CACHE_AT = 0.0


def get(key: str) -> Any:
    """Giá trị hiệu lực của một khóa: bảng cấu hình → config.py → mặc định khai báo."""
    stored = _load().get(key)
    if stored is not None:
        return stored
    spec = SCHEMA.get(key, {})
    if spec.get("default") is not None:
        return spec["default"]
    return getattr(get_settings(), key, None)


def flag(key: str) -> bool:
    return bool(get(key))


def quota(key: str) -> int:
    value = get(key)
    return int(value) if value is not None else 0


def set_value(db: Session, key: str, value: Any, actor_email: str = "") -> Any:
    """Ghi một khóa (chỉ khóa có trong SCHEMA) rồi làm mới cache ngay.

    `None` / chuỗi rỗng = XÓA giá trị đã lưu → khóa quay về mặc định. Cần cho
    khóa hạn mức theo hạng: ô để trống nghĩa là "dùng mức chung", mà trước đây
    `int("")` ném ValueError nên không có cách nào trả một khóa về mặc định.
    """
    from app.models.admin import AppSetting
    if key not in SCHEMA:
        raise KeyError(key)
    kind = SCHEMA[key]["type"]

    if kind != "bool" and (value is None or value == ""):
        row = db.get(AppSetting, key)
        if row is not None:
            db.delete(row)
            db.commit()
        invalidate()
        return None

    value = bool(value) if kind == "bool" else int(value)

    row = db.get(AppSetting, key)
    if row is None:
        row = AppSetting(key=key, value={"v": value}, updated_by=actor_email)
        db.add(row)
    else:
        row.value = {"v": value}
        row.updated_by = actor_email
    db.commit()
    invalidate()
    return value


def snapshot() -> list[dict[str, Any]]:
    """Toàn bộ khóa + giá trị hiệu lực — dựng form Cài đặt trong /admin."""
    stored = _load()
    return [{"key": key, **spec, "value": get(key), "overridden": stored.get(key) is not None}
            for key, spec in SCHEMA.items()]
