"""Đăng nhập bằng Google (OAuth2 — luồng authorization code phía server).

Proxy `/api` của Nuxt (ofetch) TỰ ĐỘNG đi theo redirect phía máy chủ, nên ở đây
KHÔNG trả mã 3xx qua proxy:

  · GET /auth/google/start    → trả JSON {url}; frontend tự `window.location = url`.
  · GET /auth/google/callback → trả một trang HTML nhỏ: đặt cookie đăng nhập rồi
    để TRÌNH DUYỆT tự `location.replace(next)`. Set-Cookie đi qua proxy vẫn tới
    trình duyệt (giống hệt luồng đăng nhập bằng mật khẩu đang chạy).

Mọi Set-Cookie phải đặt lên CHÍNH response HTML trả về — vì khi trả một
HTMLResponse tùy biến thì cookie mà dependency đặt lên `Response` tiêm sẽ mất.
"""
from __future__ import annotations

import base64
import binascii
import json
import secrets
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_device
from app.api.routes.auth import _set_auth_cookie
from app.core import fingerprint, ratelimit, settings_store
from app.core.config import get_settings
from app.core.security import create_purpose_token, decode_purpose_token
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/auth/google", tags=["auth"])

_AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URI = "https://oauth2.googleapis.com/token"
_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
_STATE_PURPOSE = "oauth-google-state"
_STATE_COOKIE = "g_oauth_state"
_STATE_TTL_MIN = 10


def _safe_next(raw: str) -> str:
    """Chỉ cho điều hướng NỘI BỘ: bắt đầu "/" và không phải "//" hay có scheme."""
    if raw.startswith("/") and not raw.startswith("//") and "://" not in raw:
        return raw
    return "/"


def _redirect_html(to: str) -> str:
    """Trang HTML điều hướng bằng JS (không phải 3xx) để đi lọt qua proxy /api."""
    #  `to` luôn do ta dựng (đường dẫn nội bộ đã lọc) nên an toàn; vẫn khử ký tự
    #  có thể phá chuỗi JS/attribute cho chắc.
    safe = to.replace("\\", "").replace('"', "%22").replace("<", "%3C")
    return (
        "<!doctype html><html lang=vi><head><meta charset=utf-8>"
        f'<meta http-equiv="refresh" content="0;url={safe}">'
        "<title>Đang đăng nhập…</title></head><body style=\"font-family:sans-serif;"
        "background:#070b16;color:#eef3ff;display:grid;place-items:center;height:100vh\">"
        f'<script>location.replace("{safe}")</script>'
        f'<p>Đang đưa bạn quay lại… <a style="color:#5ac8ff" href="{safe}">bấm vào đây</a> '
        "nếu chờ lâu.</p></body></html>"
    )


def _fail(message: str) -> HTMLResponse:
    """Về trang đăng nhập kèm thông báo lỗi (frontend đọc ?oauth_error=)."""
    html = HTMLResponse(_redirect_html("/login?" + urlencode({"oauth_error": message})))
    html.delete_cookie(_STATE_COOKIE, path="/")
    return html


def _decode_jwt_segment(seg: str) -> dict:
    pad = "=" * (-len(seg) % 4)
    return json.loads(base64.urlsafe_b64decode(seg + pad))


@router.get("/start", summary="Bắt đầu đăng nhập Google (trả URL để frontend chuyển hướng)")
def google_start(response: Response, next: str = "/", app: str = "web",
                 fp_hash: str = Depends(get_device),
                 db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    if not settings.google_oauth_enabled:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Đăng nhập Google chưa được cấu hình.")
    #  Trang quản trị (:3020 / admin.<domain>) dùng redirect URI RIÊNG để Google
    #  gọi về đúng origin admin — cookie đăng nhập đặt tại đó, không phải chia sẻ
    #  với app công khai. Cờ `admin` ký vào state để /callback dùng lại y hệt.
    is_admin = app == "admin"
    redirect_uri = (settings.google_admin_redirect_uri if is_admin
                    else settings.google_redirect_uri)
    #  State ký (chống giả mạo callback) + cookie sid đối chiếu (double-submit).
    sid = secrets.token_urlsafe(16)
    state = create_purpose_token(0, _STATE_PURPOSE, _STATE_TTL_MIN,
                                 extra={"next": _safe_next(next), "sid": sid,
                                        "admin": is_admin})
    params = urlencode({
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    })
    #  Đặt lên response tiêm (cùng với cookie `did` mà get_device đã đặt) rồi trả
    #  dict — FastAPI gộp header của response tiêm vào phản hồi.
    response.set_cookie(_STATE_COOKIE, sid, max_age=_STATE_TTL_MIN * 60, httponly=True,
                        secure=settings.cookie_secure, samesite="lax", path="/")
    return {"url": f"{_AUTH_URI}?{params}"}


@router.get("/callback", summary="Google gọi lại sau khi người dùng đồng ý")
def google_callback(request: Request, code: str = "", state: str = "", error: str = "",
                    db: Session = Depends(get_db)) -> HTMLResponse:
    settings = get_settings()
    if not settings.google_oauth_enabled:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Đăng nhập Google chưa được cấu hình.")

    if error:
        return _fail("Bạn đã hủy đăng nhập Google." if error == "access_denied"
                     else "Đăng nhập Google không thành công.")

    claims = decode_purpose_token(state, _STATE_PURPOSE)
    sid_cookie = request.cookies.get(_STATE_COOKIE, "")
    if claims is None or not code or not sid_cookie or claims.get("sid") != sid_cookie:
        return _fail("Phiên đăng nhập Google không hợp lệ hoặc đã hết hạn. Thử lại.")
    next_to = _safe_next(str(claims.get("next", "/")))
    #  Cùng cờ đã ký ở /start → chọn ĐÚNG redirect_uri Google yêu cầu khớp khi đổi
    #  token (dùng sai sẽ bị Google từ chối).
    is_admin_flow = bool(claims.get("admin"))
    redirect_uri = (settings.google_admin_redirect_uri if is_admin_flow
                    else settings.google_redirect_uri)

    #  Đổi code lấy token: server-to-server qua TLS tin cậy.
    try:
        resp = httpx.post(_TOKEN_URI, data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }, timeout=10.0)
    except httpx.HTTPError:
        return _fail("Không kết nối được tới Google. Thử lại sau.")
    if resp.status_code != 200:
        return _fail("Google từ chối mã đăng nhập. Thử lại.")

    id_token = resp.json().get("id_token", "")
    parts = id_token.split(".")
    if len(parts) != 3:
        return _fail("Google trả về dữ liệu không hợp lệ.")
    try:
        payload = _decode_jwt_segment(parts[1])
    except (binascii.Error, ValueError):
        return _fail("Google trả về dữ liệu không hợp lệ.")

    #  id_token lấy TRỰC TIẾP từ token endpoint qua TLS nên không cần kiểm chữ ký,
    #  nhưng vẫn soi claim: đúng ứng dụng của mình, đúng nơi phát, còn hạn.
    if payload.get("aud") != settings.google_client_id:
        return _fail("Mã đăng nhập không thuộc ứng dụng này.")
    if payload.get("iss") not in _ISSUERS:
        return _fail("Nguồn phát mã đăng nhập không hợp lệ.")
    try:
        if float(payload.get("exp", 0)) < time.time():
            return _fail("Mã đăng nhập đã hết hạn. Thử lại.")
    except (TypeError, ValueError):
        return _fail("Google trả về dữ liệu không hợp lệ.")

    sub = str(payload.get("sub") or "")
    email = str(payload.get("email") or "").lower().strip()
    email_verified = bool(payload.get("email_verified"))
    name = str(payload.get("name") or "").strip()
    if not sub or not email:
        return _fail("Google không cung cấp đủ thông tin tài khoản.")

    #  Trang HTML điều hướng — MỌI Set-Cookie đặt lên chính response này.
    html = HTMLResponse(_redirect_html(next_to))
    html.delete_cookie(_STATE_COOKIE, path="/")

    device_id = fingerprint.ensure_device_cookie(request, html)
    fp_hash = fingerprint.fingerprint(request, device_id)

    #  ── Luồng QUẢN TRỊ ──────────────────────────────────────────────────────
    #  Cửa quản trị đọc được dữ liệu mọi người dùng: KHÔNG tự tạo tài khoản, chỉ
    #  cho vào nếu Google khớp một tài khoản ĐÃ có quyền admin. Không đặt cookie
    #  cho bất kỳ ai khác — để cửa này không thành nơi đẻ tài khoản.
    if is_admin_flow:
        admin = db.scalar(select(User).where(User.oauth_sub == sub))
        #  Chưa gắn Google mà email đã kiểm chứng → cho khớp theo email để admin
        #  cũ (đăng nhập mật khẩu) lần đầu dùng được Google. Email chưa kiểm
        #  chứng thì KHÔNG khớp, tránh mạo danh admin qua email trùng.
        if admin is None and email_verified:
            admin = db.scalar(select(User).where(User.email == email))
        if admin is None or admin.role != "admin":
            return _fail("Tài khoản Google này không có quyền quản trị.")
        if admin.status and admin.status != "active":
            return _fail("Tài khoản đang bị tạm khóa. Liên hệ hỗ trợ để mở lại.")
        if not admin.oauth_sub:
            admin.oauth_sub = sub
        if admin.email_verified_at is None and email_verified:
            admin.email_verified_at = datetime.now(timezone.utc)
        admin.last_login_at = func.now()
        admin.last_ip = ratelimit.client_ip(request)
        db.commit()
        db.refresh(admin)
        fingerprint.record(db, fp_hash, request, admin.id)
        _set_auth_cookie(html, admin)
        return html

    blocked, reason = fingerprint.is_blocked(db, fp_hash)
    if blocked:
        return _fail(reason or "Thiết bị này đang bị hạn chế.")

    user = db.scalar(select(User).where(User.oauth_sub == sub))
    if user is None:
        existing = db.scalar(select(User).where(User.email == email))
        if existing is not None:
            #  Đã có tài khoản cùng email → GẮN Google vào, NHƯNG chỉ khi Google
            #  xác nhận email đã kiểm chứng: nếu không, kẻ tạo email chưa kiểm
            #  chứng trên Google trùng địa chỉ người khác có thể chiếm tài khoản.
            if not email_verified:
                return _fail("Email Google này chưa được xác minh nên không thể liên kết.")
            existing.oauth_sub = sub
            if existing.email_verified_at is None:
                existing.email_verified_at = datetime.now(timezone.utc)
            user = existing
        else:
            #  Tạo tài khoản mới — vẫn chịu trần số tài khoản/thiết bị như đăng ký
            #  thường, để Google không thành cửa lách việc nuôi nhiều tài khoản.
            max_accounts = (settings_store.quota("max_accounts_per_device")
                            or settings.max_accounts_per_device)
            if fingerprint.accounts_on_device(db, fp_hash) >= max_accounts:
                return _fail(f"Thiết bị này đã tạo {max_accounts} tài khoản. "
                             "Liên hệ hỗ trợ nếu bạn thực sự cần thêm.")
            user = User(
                email=email,
                display_name=name or email.split("@")[0],
                password_hash="",
                auth_provider="google",
                oauth_sub=sub,
                email_verified_at=datetime.now(timezone.utc) if email_verified else None,
                last_ip=ratelimit.client_ip(request),
            )
            db.add(user)

    #  User vừa tạo chưa flush nên status còn None (default "active" áp lúc flush)
    #  → chỉ chặn khi đã có giá trị KHÁC "active" (tài khoản cũ bị khóa).
    if user.status and user.status != "active":
        return _fail("Tài khoản đang bị tạm khóa. Liên hệ hỗ trợ để mở lại.")

    user.last_login_at = func.now()
    user.last_ip = ratelimit.client_ip(request)
    db.commit()
    db.refresh(user)
    fingerprint.record(db, fp_hash, request, user.id)
    _set_auth_cookie(html, user)
    return html
