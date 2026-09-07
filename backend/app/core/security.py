"""Băm mật khẩu (bcrypt) và ký/giải JWT (token xác thực)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings

#  bcrypt chỉ dùng tối đa 72 BYTE đầu của mật khẩu; cắt trước cho nhất quán và
#  tránh cảnh báo của thư viện khi mật khẩu (dạng byte) dài hơn ngưỡng này.
_BCRYPT_MAX_BYTES = 72


def _clip(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_clip(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_clip(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str | int, token_version: int = 0) -> str:
    """Ký JWT với `sub` = id người dùng, `tv` = phiên bản token, và hạn dùng.

    `tv` (token version) là cách THU HỒI phiên đã cấp: token sống 7 ngày, nên
    nếu không có nó thì đổi mật khẩu xong kẻ trộm vẫn dùng tiếp token cũ đủ một
    tuần. Tăng `users.token_version` là mọi token cũ hết hiệu lực ngay.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "tv": token_version,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> tuple[str, int] | None:
    """Trả `(sub, token_version)` nếu token hợp lệ, ngược lại None.

    Token cũ (ký trước khi có `tv`) coi như phiên bản 0 — không đá người đang
    đăng nhập ra ngoài chỉ vì nâng cấp.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    sub = payload.get("sub")
    if sub is None:
        return None
    try:
        version = int(payload.get("tv", 0))
    except (TypeError, ValueError):
        version = 0
    return str(sub), version


#  ── Token dùng MỘT VIỆC: xác minh email, đặt lại mật khẩu ────────────────────
#
#  Cùng khóa ký với token đăng nhập nhưng có `purpose` riêng, nên không thể lấy
#  link xác minh email đem dùng như token đăng nhập (và ngược lại).


def create_purpose_token(subject: str | int, purpose: str, minutes: int,
                         extra: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "purpose": purpose,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    payload.update(extra or {})
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_purpose_token(token: str, purpose: str) -> dict[str, Any] | None:
    """Giải token một-việc; sai `purpose` hoặc hết hạn → None."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    if payload.get("purpose") != purpose:
        return None
    return payload
