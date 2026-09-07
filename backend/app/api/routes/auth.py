"""Route xác thực: đăng ký, đăng nhập, đăng xuất, xem thông tin bản thân.

Token đăng nhập (JWT) được đặt vào cookie **httpOnly** — JavaScript không đọc
được nên an toàn hơn trước XSS. Frontend không cần tự giữ token; trình duyệt tự
gửi cookie kèm mỗi request cùng origin (qua proxy /api của Nuxt).
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_device
from app.core import fingerprint, mailer, ratelimit, settings_store
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_purpose_token,
    decode_purpose_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    DeleteAccountRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UserOut,
)

_VERIFY = "verify-email"
_RESET = "reset-password"

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookie(response: Response, user: User) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.cookie_name,
        value=create_access_token(user.id, user.token_version),
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",  # đủ chặn CSRF cho thao tác cùng site, vẫn cho điều hướng thường
        path="/",
        domain=settings.cookie_domain or None,
    )


def _send_verification(user: User) -> None:
    """Gửi thư xác minh. Token mang theo email để đổi email là link cũ hỏng."""
    token = create_purpose_token(user.id, _VERIFY, get_settings().verify_token_minutes,
                                 extra={"email": user.email})
    mailer.send_verification(user.email, token)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED,
             summary="Đăng ký tài khoản mới")
def register(payload: RegisterRequest, request: Request, response: Response,
             fp_hash: str = Depends(get_device),
             db: Session = Depends(get_db)) -> User:
    ratelimit.enforce(request, "register")  # chống đăng ký spam theo IP
    #  Cần gạt khẩn cấp: thấy bot tạo tài khoản hàng loạt thì đóng đăng ký ngay
    #  trong /admin, người đang có tài khoản không bị ảnh hưởng.
    if not settings_store.flag("registration_open"):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Đăng ký tài khoản mới đang tạm đóng. Vui lòng quay lại sau.")
    #  Thang leo thang theo THIẾT BỊ: đăng ký thêm email trên cùng một máy là
    #  cách rẻ nhất để nhân hạn mức. Tài khoản cũ trên máy đó vẫn dùng bình thường.
    max_accounts = get_settings().max_accounts_per_device
    if fingerprint.accounts_on_device(db, fp_hash) >= max_accounts:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Thiết bị này đã tạo {max_accounts} tài khoản. "
                   "Nếu bạn thực sự cần thêm, vui lòng liên hệ hỗ trợ.")
    email = payload.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email này đã được đăng ký.")

    user = User(
        email=email,
        display_name=payload.display_name.strip() or email.split("@")[0],
        password_hash=hash_password(payload.password),
        last_ip=ratelimit.client_ip(request),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    fingerprint.record(db, fp_hash, request, user.id)
    _send_verification(user)
    _set_auth_cookie(response, user)  # đăng ký xong đăng nhập luôn (nhưng chưa xác minh)
    return user


@router.post("/login", response_model=UserOut, summary="Đăng nhập")
def login(payload: LoginRequest, request: Request, response: Response,
          fp_hash: str = Depends(get_device),
          db: Session = Depends(get_db)) -> User:
    ratelimit.enforce(request, "login")  # chặn dò mật khẩu theo IP
    email = payload.email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    #  Cùng một thông báo cho "sai email" và "sai mật khẩu" — không tiết lộ
    #  email nào đã tồn tại trong hệ thống.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Email hoặc mật khẩu không đúng.")

    if user.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            detail="Tài khoản đang bị tạm khóa. Liên hệ hỗ trợ để mở lại.")

    #  Đã bật 2 lớp thì mật khẩu đúng vẫn chưa đủ.
    if user.totp_secret:
        import pyotp
        if not payload.totp_code:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                                detail="Nhập mã 6 số từ ứng dụng xác thực.")
        if not pyotp.TOTP(user.totp_secret).verify(payload.totp_code, valid_window=1):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Mã 6 số không đúng.")

    ratelimit.clear(request, "login")  # đăng nhập đúng → xóa bộ đếm cho IP này
    user.last_login_at = func.now()
    user.last_ip = ratelimit.client_ip(request)
    db.commit()
    db.refresh(user)
    #  Gắn tài khoản với thiết bị: đây là dữ liệu để phát hiện một máy nuôi
    #  nhiều tài khoản (trang Thiết bị của /admin ở pha S3).
    fingerprint.record(db, fp_hash, request, user.id)
    _set_auth_cookie(response, user)
    return user


@router.post("/logout", summary="Đăng xuất")
def logout(response: Response) -> dict[str, str]:
    settings = get_settings()
    response.delete_cookie(settings.cookie_name, path="/",
                           domain=settings.cookie_domain or None)
    return {"detail": "Đã đăng xuất."}


@router.get("/me", response_model=UserOut, summary="Thông tin tài khoản đang đăng nhập")
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT,
             summary="Đổi mật khẩu (đang đăng nhập)")
def change_password(payload: ChangePasswordRequest,
                    user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)) -> None:
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Mật khẩu hiện tại không đúng.")
    user.password_hash = hash_password(payload.new_password)
    #  THU HỒI mọi phiên cũ: token sống 7 ngày, nếu không tăng số này thì kẻ đã
    #  trộm được cookie vẫn dùng tiếp cả tuần dù nạn nhân đã đổi mật khẩu.
    user.token_version += 1
    db.commit()


@router.post("/verify", response_model=UserOut, summary="Xác minh email bằng token trong thư")
def verify_email(token: str, response: Response, db: Session = Depends(get_db)) -> User:
    claims = decode_purpose_token(token, _VERIFY)
    if claims is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail="Liên kết xác minh không hợp lệ hoặc đã hết hạn.")
    user = db.get(User, int(claims["sub"])) if str(claims["sub"]).isdigit() else None
    #  Đối chiếu cả email: đổi email xong thì link cũ phải hỏng.
    if user is None or user.email != claims.get("email"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Liên kết xác minh không hợp lệ.")
    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
    _set_auth_cookie(response, user)  # xác minh xong dùng được ngay, không cần đăng nhập lại
    return user


@router.post("/resend-verification", status_code=status.HTTP_202_ACCEPTED,
             summary="Gửi lại thư xác minh")
def resend_verification(request: Request, user: User = Depends(get_current_user)) -> dict[str, str]:
    ratelimit.enforce(request, "resend-verify")  # chống dùng hệ thống thư để spam
    if user.email_verified_at is not None:
        return {"detail": "Email này đã được xác minh."}
    _send_verification(user)
    return {"detail": "Đã gửi lại thư xác minh. Vui lòng kiểm tra hộp thư."}


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED,
             summary="Quên mật khẩu — gửi link đặt lại")
def forgot_password(payload: ForgotPasswordRequest, request: Request,
                    db: Session = Depends(get_db)) -> dict[str, str]:
    ratelimit.enforce(request, "forgot-password")
    email = payload.email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    if user is not None and user.status == "active":
        #  Token gắn với hash mật khẩu HIỆN TẠI → dùng một lần: đổi xong là hash
        #  đổi, link cũ tự hỏng, không cần bảng lưu token đã dùng.
        token = create_purpose_token(
            user.id, _RESET, get_settings().reset_token_minutes,
            extra={"pw": user.password_hash[-16:]})
        mailer.send_password_reset(user.email, token)
    #  Trả lời GIỐNG NHAU dù email có tồn tại hay không — nếu không, đây thành
    #  công cụ dò xem ai đã đăng ký tài khoản.
    return {"detail": "Nếu email tồn tại trong hệ thống, chúng tôi đã gửi link đặt lại mật khẩu."}


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT,
             summary="Đặt mật khẩu mới bằng token trong thư")
def reset_password(payload: ResetPasswordRequest, request: Request,
                   db: Session = Depends(get_db)) -> None:
    ratelimit.enforce(request, "reset-password")
    claims = decode_purpose_token(payload.token, _RESET)
    user = None
    if claims is not None and str(claims.get("sub", "")).isdigit():
        user = db.get(User, int(claims["sub"]))
    if user is None or claims.get("pw") != user.password_hash[-16:]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail="Liên kết đặt lại mật khẩu không hợp lệ hoặc đã dùng rồi.")
    user.password_hash = hash_password(payload.new_password)
    user.token_version += 1          # đá mọi phiên cũ ra ngoài
    if user.email_verified_at is None:
        #  Nhận được thư ở hòm thư đó ⇒ đã chứng minh sở hữu email.
        user.email_verified_at = datetime.now(timezone.utc)
    db.commit()


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT,
               summary="Xóa tài khoản của chính mình (không hoàn tác)")
def delete_account(payload: DeleteAccountRequest, response: Response,
                   user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)) -> None:
    """Quyền xóa dữ liệu của người dùng — Nghị định 13/2023 về bảo vệ dữ liệu cá nhân.

    Xóa THẬT: mã theo dõi, hội thoại, tệp đính kèm, thông báo đều xóa theo
    (khóa ngoại ON DELETE CASCADE).
    """
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Mật khẩu không đúng.")
    settings = get_settings()
    db.delete(user)
    db.commit()
    response.delete_cookie(settings.cookie_name, path="/",
                           domain=settings.cookie_domain or None)
