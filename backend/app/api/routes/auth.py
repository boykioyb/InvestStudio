"""Route xác thực: đăng ký, đăng nhập, đăng xuất, xem thông tin bản thân.

Token đăng nhập (JWT) được đặt vào cookie **httpOnly** — JavaScript không đọc
được nên an toàn hơn trước XSS. Frontend không cần tự giữ token; trình duyệt tự
gửi cookie kèm mỗi request cùng origin (qua proxy /api của Nuxt).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core import ratelimit
from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookie(response: Response, user_id: int) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.cookie_name,
        value=create_access_token(user_id),
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",  # đủ chặn CSRF cho thao tác cùng site, vẫn cho điều hướng thường
        path="/",
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED,
             summary="Đăng ký tài khoản mới")
def register(payload: RegisterRequest, request: Request, response: Response,
             db: Session = Depends(get_db)) -> User:
    ratelimit.enforce(request, "register")  # chống đăng ký spam theo IP
    email = payload.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email này đã được đăng ký.")

    user = User(
        email=email,
        display_name=payload.display_name.strip() or email.split("@")[0],
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    _set_auth_cookie(response, user.id)  # đăng ký xong đăng nhập luôn
    return user


@router.post("/login", response_model=UserOut, summary="Đăng nhập")
def login(payload: LoginRequest, request: Request, response: Response,
          db: Session = Depends(get_db)) -> User:
    ratelimit.enforce(request, "login")  # chặn dò mật khẩu theo IP
    email = payload.email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    #  Cùng một thông báo cho "sai email" và "sai mật khẩu" — không tiết lộ
    #  email nào đã tồn tại trong hệ thống.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Email hoặc mật khẩu không đúng.")

    ratelimit.clear(request, "login")  # đăng nhập đúng → xóa bộ đếm cho IP này
    _set_auth_cookie(response, user.id)
    return user


@router.post("/logout", summary="Đăng xuất")
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(get_settings().cookie_name, path="/")
    return {"detail": "Đã đăng xuất."}


@router.get("/me", response_model=UserOut, summary="Thông tin tài khoản đang đăng nhập")
def me(user: User = Depends(get_current_user)) -> User:
    return user
