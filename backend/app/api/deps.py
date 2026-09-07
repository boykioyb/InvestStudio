"""Dependency dùng chung cho các route: lấy người dùng đang đăng nhập."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User


def _read_token(request: Request) -> str | None:
    """Ưu tiên cookie httpOnly; chấp nhận cả header Authorization: Bearer."""
    cookie_name = get_settings().cookie_name
    if token := request.cookies.get(cookie_name):
        return token
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Người dùng nếu ĐANG đăng nhập, None nếu là khách — KHÔNG raise 401.

    Dùng cho các endpoint mở cho cả khách nhưng cư xử khác nhau: khách chỉ được
    đọc cache, thành viên mới được ép crawl lại (`refresh=true`) và có hạn mức
    riêng. Nhờ vậy trang phân tích vẫn xem được mà không ai mượn được đường công
    khai để đốt hạn mức nguồn dữ liệu.
    """
    token = _read_token(request)
    sub = decode_access_token(token) if token else None
    if sub is None or not sub.isdigit():
        return None
    return db.get(User, int(sub))


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Bắt buộc đăng nhập. Raise 401 nếu thiếu / sai token hoặc user không còn."""
    token = _read_token(request)
    sub = decode_access_token(token) if token else None
    if sub is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Bạn cần đăng nhập để dùng tính năng này.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.get(User, int(sub)) if sub.isdigit() else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập không còn hợp lệ.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Chỉ cho quản trị viên. Dùng cho việc TỐN HẠN MỨC CHUNG (lập chỉ mục…).

    Trước đây `POST /chat/reindex` mở cho mọi tài khoản đã đăng nhập: một người
    lạ đăng ký xong bấm nút là đẩy job nhúng cả rổ VN30 — đủ để tiêu hết quota
    Gemini của cả ngày.
    """
    if user.role != "admin":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Chức năng này chỉ dành cho quản trị viên.")
    return user
