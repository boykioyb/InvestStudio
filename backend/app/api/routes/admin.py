"""Khu quản trị: tổng quan · người dùng · sử dụng · cài đặt · nhật ký.

Mọi endpoint đều qua `require_admin` (kèm danh sách IP cho phép và 2 lớp nếu đã
bật). Mọi thao tác GHI và mọi lần XEM dữ liệu cá nhân của một người cụ thể đều
để lại một dòng `audit_logs` — ghi audit không chặn thao tác, nó là bằng chứng.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core import audit, budget, settings_store, usage
from app.db.session import get_db
from app.models.admin import AuditLog
from app.models.device import DeviceAccount
from app.models.rag import ChatMessage
from app.models.usage import UsageDaily
from app.models.user import User, WatchlistItem
from app.schemas.admin import (
    AdminUserList,
    AdminUserOut,
    AdminUserPatch,
    AuditOut,
    OverviewOut,
    SettingOut,
    SettingsPut,
    TopEntry,
    TotpSetupOut,
    UsagePoint,
)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _user_out(db: Session, user: User) -> AdminUserOut:
    """Hồ sơ kèm vài con số đếm — cột "bao nhiêu thiết bị" là chỗ lộ tài khoản ảo."""
    counts = {
        "watchlist_count": db.scalar(select(func.count()).select_from(WatchlistItem)
                                     .where(WatchlistItem.user_id == user.id)) or 0,
        "chat_count": db.scalar(select(func.count()).select_from(ChatMessage)
                                .where(ChatMessage.user_id == user.id)) or 0,
        "device_count": db.scalar(select(func.count()).select_from(DeviceAccount)
                                  .where(DeviceAccount.user_id == user.id)) or 0,
    }
    return AdminUserOut(
        id=user.id, email=user.email, display_name=user.display_name, role=user.role,
        status=user.status, email_verified=user.email_verified_at is not None,
        created_at=user.created_at, last_login_at=user.last_login_at, last_ip=user.last_ip,
        **counts)


# ── Tổng quan ────────────────────────────────────────────────────────────────

@router.get("/overview", response_model=OverviewOut, summary="Thẻ số + chuỗi 30 ngày")
def overview(days: int = Query(30, ge=7, le=90), db: Session = Depends(get_db)) -> OverviewOut:
    from app.services.rag import store

    today = date.today()
    since = today - timedelta(days=days - 1)
    midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    counters = usage.today_counters()
    chat_today = counters.get("chat", {}).get("count", 0)
    analyze_today = counters.get("analyze", {}).get("count", 0)
    errors_today = sum(c.get("errors", 0) for c in counters.values())
    total_today = max(1, chat_today + analyze_today)

    #  Chuỗi thời gian lấy từ bảng TỔNG HỢP (usage_daily) — /admin không được
    #  quét bảng sự kiện thô mỗi lần mở.
    rows = db.execute(
        select(UsageDaily.day, UsageDaily.kind, func.sum(UsageDaily.count),
               func.sum(UsageDaily.calls), func.sum(UsageDaily.tokens_in),
               func.sum(UsageDaily.tokens_out), func.sum(UsageDaily.error_count))
        .where(UsageDaily.day >= since, UsageDaily.user_id == 0)
        .group_by(UsageDaily.day, UsageDaily.kind)
        .order_by(UsageDaily.day)).all()

    top_user_ids = usage.top_today("user")
    emails = dict(db.execute(
        select(User.id, User.email)
        .where(User.id.in_([int(k) for k, _ in top_user_ids if k.isdigit()] or [0]))).all())

    snapshot = budget.status_snapshot()
    documents, tickers = store.stats(db)

    return OverviewOut(
        users_total=db.scalar(select(func.count()).select_from(User)) or 0,
        users_new_today=db.scalar(select(func.count()).select_from(User)
                                  .where(User.created_at >= midnight)) or 0,
        users_verified=db.scalar(select(func.count()).select_from(User)
                                 .where(User.email_verified_at.is_not(None))) or 0,
        active_today=len(top_user_ids),
        chat_today=chat_today,
        analyze_today=analyze_today,
        gemini_used=snapshot["used"], gemini_cap=snapshot["cap"],
        gemini_ratio=snapshot["ratio"], gemini_level=snapshot["level"],
        error_rate_today=round(errors_today / total_today, 4),
        rag_documents=documents, rag_tickers=tickers,
        queue_running=False,
        series=[UsagePoint(day=r[0], kind=r[1], count=r[2] or 0, calls=r[3] or 0,
                           tokens_in=r[4] or 0, tokens_out=r[5] or 0, error_count=r[6] or 0)
                for r in rows],
        top_users=[TopEntry(key=k, label=emails.get(int(k), k) if k.isdigit() else k, count=c)
                   for k, c in top_user_ids],
        top_tickers=[TopEntry(key=k, label=k, count=c) for k, c in usage.top_today("ticker")],
    )


# ── Người dùng ───────────────────────────────────────────────────────────────

@router.get("/users", response_model=AdminUserList, summary="Danh sách người dùng")
def list_users(q: str = Query("", max_length=120),
               role: str = Query("", pattern="^(user|admin)?$"),
               status_filter: str = Query("", alias="status", pattern="^(active|suspended)?$"),
               page: int = Query(1, ge=1), size: int = Query(25, ge=1, le=100),
               db: Session = Depends(get_db)) -> AdminUserList:
    query = select(User)
    if q:
        like = f"%{q.lower()}%"
        query = query.where(or_(func.lower(User.email).like(like),
                                func.lower(User.display_name).like(like)))
    if role:
        query = query.where(User.role == role)
    if status_filter:
        query = query.where(User.status == status_filter)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(User.created_at.desc())
                      .offset((page - 1) * size).limit(size)).all()
    return AdminUserList(items=[_user_out(db, u) for u in rows], total=total, page=page,
                         pages=max(1, -(-total // size)))


@router.get("/users/{user_id}", response_model=AdminUserOut, summary="Hồ sơ một người dùng")
def get_user(user_id: int, request: Request, admin: User = Depends(require_admin),
             db: Session = Depends(get_db)) -> AdminUserOut:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy người dùng.")
    #  Xem hồ sơ một người cụ thể = đọc dữ liệu cá nhân → ghi vết (không chặn).
    audit.log(db, admin, "view_user_data", request=request, target_type="user", target_id=user_id)
    return _user_out(db, user)


@router.patch("/users/{user_id}", response_model=AdminUserOut, summary="Sửa vai trò/trạng thái")
def patch_user(user_id: int, payload: AdminUserPatch, request: Request,
               admin: User = Depends(require_admin),
               db: Session = Depends(get_db)) -> AdminUserOut:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy người dùng.")
    if user.id == admin.id and payload.role == "user":
        #  Chặn tự hạ quyền chính mình → tránh trường hợp không còn admin nào.
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail="Không thể tự bỏ quyền quản trị của chính mình.")

    before = {"role": user.role, "status": user.status,
              "email_verified": user.email_verified_at is not None}
    if payload.role is not None:
        user.role = payload.role
    if payload.status is not None:
        if payload.status == "suspended" and user.status != "suspended":
            user.token_version += 1     # khóa là đá mọi phiên đang mở ra ngoài
        user.status = payload.status
    if payload.email_verified is not None:
        user.email_verified_at = (datetime.now(timezone.utc)
                                  if payload.email_verified else None)
    db.commit()
    db.refresh(user)

    after = {"role": user.role, "status": user.status,
             "email_verified": user.email_verified_at is not None}
    audit.log(db, admin, "update_user", request=request, target_type="user", target_id=user_id,
              before=before, after=after, reason=payload.reason)
    return _user_out(db, user)


@router.post("/users/{user_id}/revoke-sessions", status_code=status.HTTP_204_NO_CONTENT,
             summary="Thu hồi mọi phiên đăng nhập của người dùng")
def revoke_sessions(user_id: int, request: Request, admin: User = Depends(require_admin),
                    db: Session = Depends(get_db)) -> None:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy người dùng.")
    user.token_version += 1
    db.commit()
    audit.log(db, admin, "revoke_sessions", request=request, target_type="user",
              target_id=user_id)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Xóa tài khoản (không hoàn tác)")
def delete_user(user_id: int, request: Request, reason: str = Query("", max_length=500),
                admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> None:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy người dùng.")
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail="Dùng trang tài khoản để tự xóa chính mình.")
    snapshot = {"email": user.email, "role": user.role, "status": user.status}
    db.delete(user)
    db.commit()
    audit.log(db, admin, "delete_user", request=request, target_type="user", target_id=user_id,
              before=snapshot, reason=reason)


# ── Sử dụng ──────────────────────────────────────────────────────────────────

@router.get("/usage", response_model=list[UsagePoint], summary="Số liệu dùng theo ngày")
def usage_series(days: int = Query(30, ge=1, le=180),
                 db: Session = Depends(get_db)) -> list[UsagePoint]:
    since = date.today() - timedelta(days=days - 1)
    rows = db.execute(
        select(UsageDaily.day, UsageDaily.kind, func.sum(UsageDaily.count),
               func.sum(UsageDaily.calls), func.sum(UsageDaily.tokens_in),
               func.sum(UsageDaily.tokens_out), func.sum(UsageDaily.error_count))
        .where(UsageDaily.day >= since, UsageDaily.user_id == 0)
        .group_by(UsageDaily.day, UsageDaily.kind).order_by(UsageDaily.day)).all()
    return [UsagePoint(day=r[0], kind=r[1], count=r[2] or 0, calls=r[3] or 0,
                       tokens_in=r[4] or 0, tokens_out=r[5] or 0, error_count=r[6] or 0)
            for r in rows]


# ── Cài đặt & cần gạt khẩn cấp ───────────────────────────────────────────────

@router.get("/settings", response_model=list[SettingOut], summary="Cấu hình chạy")
def get_settings_list() -> list[SettingOut]:
    return [SettingOut(**item) for item in settings_store.snapshot()]


@router.put("/settings", response_model=list[SettingOut], summary="Đổi cấu hình (hiệu lực ≤30s)")
def put_settings(payload: SettingsPut, request: Request, admin: User = Depends(require_admin),
                 db: Session = Depends(get_db)) -> list[SettingOut]:
    before = {item["key"]: item["value"] for item in settings_store.snapshot()}
    changed: dict[str, object] = {}
    for key, value in payload.values.items():
        try:
            changed[key] = settings_store.set_value(db, key, value, actor_email=admin.email)
        except (KeyError, ValueError, TypeError) as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                detail=f"Cấu hình không hợp lệ: {key}") from exc
    audit.log(db, admin, "update_settings", request=request, target_type="settings",
              before={k: before.get(k) for k in changed}, after=changed, reason=payload.reason)
    return [SettingOut(**item) for item in settings_store.snapshot()]


# ── Nhật ký kiểm toán ────────────────────────────────────────────────────────

@router.get("/audit", response_model=list[AuditOut], summary="Nhật ký thao tác quản trị")
def audit_log(action: str = Query("", max_length=64), limit: int = Query(100, ge=1, le=500),
              db: Session = Depends(get_db)) -> list[AuditLog]:
    query = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
    if action:
        query = query.where(AuditLog.action == action)
    return list(db.scalars(query).all())


# ── Xác thực 2 lớp cho tài khoản quản trị ────────────────────────────────────

@router.post("/2fa/setup", response_model=TotpSetupOut, summary="Tạo khóa 2 lớp (chưa bật)")
def totp_setup(request: Request, admin: User = Depends(require_admin),
               db: Session = Depends(get_db)) -> TotpSetupOut:
    """Sinh khóa mới. CHƯA lưu vào tài khoản — chỉ bật sau khi nhập đúng mã 6 số,
    nếu không lỡ quét hỏng là tự khóa mình ngoài cửa."""
    import pyotp

    secret = pyotp.random_base32()
    #  Giữ tạm trong Redis 10 phút thay vì ghi thẳng vào tài khoản.
    from app.core.ratelimit import redis_client
    redis_client().set(f"totp:pending:{admin.id}", secret, ex=600)
    url = pyotp.TOTP(secret).provisioning_uri(name=admin.email, issuer_name="InvestStudio")
    audit.log(db, admin, "totp_setup", request=request, target_type="user", target_id=admin.id)
    return TotpSetupOut(secret=secret, otpauth_url=url)


@router.post("/2fa/enable", status_code=status.HTTP_204_NO_CONTENT, summary="Bật 2 lớp")
def totp_enable(code: str = Query(..., min_length=6, max_length=8), request: Request = None,
                admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> None:
    import pyotp

    from app.core.ratelimit import redis_client
    raw = redis_client().get(f"totp:pending:{admin.id}")
    if not raw:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail="Chưa có khóa đang chờ, hãy tạo lại mã QR.")
    secret = raw.decode()
    if not pyotp.TOTP(secret).verify(code, valid_window=1):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Mã 6 số không đúng.")
    admin.totp_secret = secret
    #  Đá mọi phiên cũ: từ giờ đăng nhập phải qua 2 lớp.
    admin.token_version += 1
    db.commit()
    redis_client().delete(f"totp:pending:{admin.id}")
    audit.log(db, admin, "totp_enable", request=request, target_type="user", target_id=admin.id)


@router.delete("/2fa", status_code=status.HTTP_204_NO_CONTENT, summary="Tắt 2 lớp")
def totp_disable(code: str = Query(..., min_length=6, max_length=8), request: Request = None,
                 admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> None:
    """Tắt phải nhập mã đang hiệu lực — nếu không, ai mượn được phiên là tắt được."""
    import pyotp

    if not admin.totp_secret or not pyotp.TOTP(admin.totp_secret).verify(code, valid_window=1):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Mã 6 số không đúng.")
    admin.totp_secret = ""
    db.commit()
    audit.log(db, admin, "totp_disable", request=request, target_type="user", target_id=admin.id)
