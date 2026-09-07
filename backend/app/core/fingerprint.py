"""Nhận dạng THIẾT BỊ để hạn mức không bị vô hiệu bằng cách đăng ký email mới.

Vân tay ghép từ HAI NỬA, phải giả mạo được cả hai mới lách:

1. **Phía trình duyệt** — `visitorId` do FingerprintJS tính (canvas, WebGL, phông
   chữ, âm thanh…), trình duyệt tự gửi lên qua cookie `fpjs`.
2. **Phía máy chủ** — cookie `did` **httpOnly có ký**: JavaScript không đọc được,
   `curl` tự chế cũng không ký nổi vì không có khóa bí mật.

Cộng thêm dòng trình duyệt và ngôn ngữ. Kết quả băm SHA-256 → `fp_hash`.

⚠️ Nói rõ giới hạn (docs/SHIP_PLAN.md §2.4): đổi trình duyệt, bật chống-
fingerprint của Brave/Firefox, hay dùng máy khác thì vân tay đổi hẳn — chặn được
kiểu "tiện tay lách" (ẩn danh, xóa cookie, đổi IP, đăng ký lại) chứ KHÔNG chặn
được người quyết tâm. Nó là lớp ma sát; lớp bảo đảm là trần toàn cục ở
`app/core/budget.py`.

⚠️ Vân tay thiết bị là DỮ LIỆU CÁ NHÂN theo Nghị định 13/2023 — chính sách quyền
riêng tư phải nêu rõ việc thu thập này để chống lạm dụng hạn mức.
"""
from __future__ import annotations

import hashlib
import ipaddress
import sys
import uuid

from fastapi import Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.ratelimit import client_ip
from app.core.security import create_purpose_token, decode_purpose_token

DEVICE_COOKIE = "did"        # id thiết bị do máy chủ cấp (httpOnly, có ký)
CLIENT_COOKIE = "fpjs"       # visitorId do FingerprintJS tính phía trình duyệt
_PURPOSE = "device"
_TEN_YEARS_MINUTES = 60 * 24 * 365 * 10


def _ua_family(user_agent: str) -> str:
    """Rút gọn User-Agent về "dòng" trình duyệt.

    Dùng nguyên chuỗi UA thì mỗi lần Chrome tự cập nhật là vân tay đổi, hạn mức
    tự reset — đúng thứ ta đang muốn chặn.
    """
    ua = user_agent.lower()
    for name in ("edg", "opr", "firefox", "chrome", "safari"):
        if name in ua:
            platform = next((p for p in ("android", "iphone", "ipad", "mac", "windows", "linux")
                             if p in ua), "khac")
            return f"{name}:{platform}"
    return "khac"


def ensure_device_cookie(request: Request, response: Response) -> str:
    """Đọc id thiết bị từ cookie đã ký; chưa có/ hỏng thì cấp mới và đặt cookie."""
    settings = get_settings()
    raw = request.cookies.get(DEVICE_COOKIE, "")
    if raw:
        claims = decode_purpose_token(raw, _PURPOSE)
        if claims and claims.get("sub"):
            return str(claims["sub"])

    device_id = uuid.uuid4().hex
    token = create_purpose_token(device_id, _PURPOSE, _TEN_YEARS_MINUTES)
    response.set_cookie(
        key=DEVICE_COOKIE, value=token, max_age=60 * 60 * 24 * 365,
        httponly=True, secure=settings.cookie_secure, samesite="lax", path="/",
        domain=settings.cookie_domain or None,
    )
    return device_id


def fingerprint(request: Request, device_id: str) -> str:
    """Băm vân tay từ 4 mảnh: visitorId · id thiết bị · dòng trình duyệt · ngôn ngữ."""
    visitor = (request.headers.get("x-device-id")
               or request.cookies.get(CLIENT_COOKIE, ""))[:120]
    parts = "|".join((
        visitor,
        device_id,
        _ua_family(request.headers.get("user-agent", "")),
        request.headers.get("accept-language", "")[:40],
    ))
    return hashlib.sha256(parts.encode("utf-8")).hexdigest()


def subnet_of(ip: str) -> str:
    """Dải /24 (IPv4) hoặc /48 (IPv6) — rổ đếm rộng cho cả một mạng.

    Đặt trần RỘNG cho rổ này: nhà mạng Việt Nam cho hàng nghìn thuê bao dùng
    chung một IP (NAT), siết chặt là chặn nhầm cả một khu.
    """
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    if addr.version == 4:
        return str(ipaddress.ip_network(f"{ip}/24", strict=False))
    return str(ipaddress.ip_network(f"{ip}/48", strict=False))


def record(db: Session, fp_hash: str, request: Request, user_id: int | None) -> None:
    """Ghi nhận lượt dùng của thiết bị + gắn tài khoản (cho trang /admin sau này).

    Mọi lỗi ở đây bị nuốt: đây là số liệu quan sát, không được làm hỏng request
    thật của người dùng.
    """
    from app.models.device import DeviceAccount, DeviceFingerprint
    try:
        row = db.get(DeviceFingerprint, fp_hash)
        if row is None:
            row = DeviceFingerprint(fp_hash=fp_hash)
            db.add(row)
        row.user_agent = request.headers.get("user-agent", "")[:300]
        row.accept_language = request.headers.get("accept-language", "")[:120]
        row.last_ip = client_ip(request)[:45]
        row.request_count = (row.request_count or 0) + 1
        row.last_seen = func.now()

        if user_id is not None:
            link = db.get(DeviceAccount, (fp_hash, user_id))
            if link is None:
                db.add(DeviceAccount(fp_hash=fp_hash, user_id=user_id))
                row.account_count = (row.account_count or 0) + 1
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(f"[fingerprint] không ghi được: {exc}", file=sys.stderr)


def is_blocked(db: Session, fp_hash: str) -> tuple[bool, str]:
    from app.models.device import DeviceFingerprint
    row = db.get(DeviceFingerprint, fp_hash)
    if row is None or not row.blocked:
        return False, ""
    return True, row.blocked_reason or "Thiết bị này đã bị hạn chế."


def accounts_on_device(db: Session, fp_hash: str) -> int:
    from app.models.device import DeviceAccount
    return db.scalar(select(func.count()).select_from(DeviceAccount)
                     .where(DeviceAccount.fp_hash == fp_hash)) or 0
