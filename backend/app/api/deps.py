"""Dependency dùng chung cho các route: lấy người dùng đang đăng nhập."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core import fingerprint, ratelimit
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
    claims = decode_access_token(token) if (token := _read_token(request)) else None
    if claims is None:
        return None
    sub, version = claims
    if not sub.isdigit():
        return None
    user = db.get(User, int(sub))
    if user is None or user.token_version != version or user.status != "active":
        return None
    return user


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Bắt buộc đăng nhập. Raise 401 nếu thiếu / sai token hoặc user không còn."""
    claims = decode_access_token(token) if (token := _read_token(request)) else None
    if claims is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Bạn cần đăng nhập để dùng tính năng này.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    sub, version = claims
    user = db.get(User, int(sub)) if sub.isdigit() else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập không còn hợp lệ.")
    #  Token cũ hơn phiên bản hiện tại → đã bị thu hồi (đổi mật khẩu / bị khóa).
    if user.token_version != version:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập đã hết hiệu lực. Vui lòng đăng nhập lại.")
    if user.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            detail="Tài khoản đang bị tạm khóa. Liên hệ hỗ trợ để mở lại.")
    return user


#  Hai đường được miễn kiểm 2 lớp, nếu không sẽ tự nhốt mình bên ngoài: chưa bật
#  2FA thì phải vào được đúng hai endpoint để bật nó.
_TWO_FACTOR_EXEMPT = ("/api/admin/2fa/setup", "/api/admin/2fa/enable")


def require_admin(request: Request, user: User = Depends(get_current_user)) -> User:
    """Chỉ cho quản trị viên, kèm hai rào ngoài: danh sách IP và 2 lớp (TOTP).

    Trước đây `POST /chat/reindex` mở cho mọi tài khoản đã đăng nhập: một người
    lạ đăng ký xong bấm nút là đẩy job nhúng cả rổ VN30 — đủ để tiêu hết quota
    Gemini của cả ngày. Nay khu quản trị còn đọc được dữ liệu của mọi người
    dùng, nên rào phải dày hơn hẳn phần còn lại.
    """
    settings = get_settings()
    if user.role != "admin":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Chức năng này chỉ dành cho quản trị viên.")

    allowlist = settings.admin_ip_allowlist
    if allowlist and not ratelimit.ip_in_list(ratelimit.client_ip(request), allowlist):
        #  Cố ý trả 404: đừng xác nhận với người lạ rằng ở đây CÓ khu quản trị.
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not Found")

    if (settings.admin_require_2fa and not user.totp_secret
            and not request.url.path.startswith(_TWO_FACTOR_EXEMPT)):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Tài khoản quản trị phải bật xác thực 2 lớp trước khi dùng khu quản trị.",
            #  Header để giao diện PHÂN BIỆT được "thiếu 2 lớp" với "không có
            #  quyền": cái đầu sửa được ngay (đi bật), cái sau thì không.
            headers={"X-Admin-Setup": "totp"})
    return user


def require_verified(user: User = Depends(get_current_user)) -> User:
    """Bắt buộc đã xác minh email cho các tính năng TỐN HẠN MỨC CHUNG.

    Không có rào này thì hạn mức theo tài khoản là vô nghĩa: đăng ký email bịa
    mất 5 giây, tạo 20 tài khoản là nhân hạn mức lên 20 lần. Xác minh email đẩy
    chi phí lách lên đủ cao để chặn phần lớn trường hợp.
    """
    if not get_settings().require_verified_email:
        return user
    if user.email_verified_at is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Bạn cần xác minh email trước khi dùng trợ lý. "
                   "Kiểm tra hộp thư hoặc bấm gửi lại thư xác minh.")
    return user


def get_device(request: Request, response: Response, db: Session = Depends(get_db)) -> str:
    """Vân tay thiết bị của người gọi (cấp cookie `did` nếu chưa có).

    Trả về `fp_hash` để các route đếm hạn mức theo THIẾT BỊ — đăng ký thêm email
    không nhân được hạn mức nữa. Thiết bị bị quản trị đánh dấu → 403 kèm lời
    nhắn liên hệ hỗ trợ (phòng khi chặn nhầm: hai máy cùng đời, cùng hệ điều
    hành, cùng trình duyệt có thể trùng vân tay).
    """
    device_id = fingerprint.ensure_device_cookie(request, response)
    fp_hash = fingerprint.fingerprint(request, device_id)
    blocked, reason = fingerprint.is_blocked(db, fp_hash)
    if blocked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=reason)
    return fp_hash
