"""Khu quản trị — phần vận hành: hội thoại · thiết bị · kho tri thức · job ·
nguồn dữ liệu · cache · thông báo.

Tách khỏi `admin.py` (tổng quan/người dùng/cài đặt/nhật ký) cho khỏi phình một
tệp. Mọi endpoint ở đây đều đã qua `require_admin` khai ở router.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core import audit
from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.db.session import get_db
from app.models.device import DeviceAccount, DeviceFingerprint
from app.models.rag import ChatMessage, Conversation, IndexJob, RagDocument
from app.models.user import Notification, User
from app.schemas.admin import (
    AdminConversation,
    AdminDevice,
    AdminMessage,
    BroadcastIn,
    BroadcastOut,
    CacheOut,
    CacheReport,
    ChatSearchHit,
    DeviceBlockIn,
    JobOut,
    ProviderOut,
    QueueOut,
    RagDocOut,
    RagStatusOut,
)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])
logger = logging.getLogger("app.admin")


def _ngay_truoc(moc: datetime | None) -> int | None:
    if moc is None:
        return None
    if moc.tzinfo is None:
        moc = moc.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - moc).days


# ── Hội thoại ────────────────────────────────────────────────────────────────

@router.get("/conversations", response_model=list[AdminConversation],
            summary="Danh sách cuộc trò chuyện (metadata)")
def list_conversations(user_id: int | None = Query(None), ticker: str = Query("", max_length=12),
                       limit: int = Query(50, ge=1, le=200),
                       db: Session = Depends(get_db)) -> list[AdminConversation]:
    dem = (select(ChatMessage.conversation_id, func.count().label("n"))
           .group_by(ChatMessage.conversation_id).subquery())
    query = (select(Conversation, User.email, func.coalesce(dem.c.n, 0))
             .join(User, User.id == Conversation.user_id, isouter=True)
             .join(dem, dem.c.conversation_id == Conversation.id, isouter=True)
             .order_by(Conversation.updated_at.desc()).limit(limit))
    if user_id:
        query = query.where(Conversation.user_id == user_id)
    if ticker:
        query = query.where(Conversation.ticker == ticker.upper())

    return [AdminConversation(id=c.id, user_id=c.user_id, user_email=email or "(đã xóa)",
                              title=c.title, ticker=c.ticker, message_count=n,
                              updated_at=c.updated_at)
            for c, email, n in db.execute(query).all()]


@router.get("/conversations/{conversation_id}/messages", response_model=list[AdminMessage],
            summary="Toàn bộ nội dung một cuộc trò chuyện")
def conversation_messages(conversation_id: int, request: Request,
                          admin: User = Depends(require_admin),
                          db: Session = Depends(get_db)) -> list[AdminMessage]:
    """Đọc nội dung riêng tư của người dùng → LUÔN ghi một dòng audit.

    Ghi audit không chặn thao tác; nó là bằng chứng khi có tranh chấp "ai đã xem
    dữ liệu của tôi", và là thứ cơ quan quản lý hỏi đầu tiên nếu lộ dữ liệu.
    """
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cuộc trò chuyện.")

    audit.log(db, admin, "view_user_data", request=request, target_type="conversation",
              target_id=conversation_id, after={"user_id": conv.user_id})

    rows = db.scalars(select(ChatMessage).where(ChatMessage.conversation_id == conversation_id)
                      .order_by(ChatMessage.id)).all()
    return [AdminMessage(id=r.id, at=r.created_at, ticker=r.ticker, question=r.question,
                         answer=r.answer, citations=r.citations or [],
                         attachments=r.attachments or []) for r in rows]


@router.get("/chat/search", response_model=list[ChatSearchHit],
            summary="Tìm toàn văn trong câu hỏi và câu trả lời")
def chat_search(q: str = Query(..., min_length=2, max_length=120),
                limit: int = Query(50, ge=1, le=200), request: Request = None,  # type: ignore[assignment]
                admin: User = Depends(require_admin),
                db: Session = Depends(get_db)) -> list[ChatSearchHit]:
    audit.log(db, admin, "search_chat", request=request, target_type="chat", after={"q": q})

    mau = f"%{q.lower()}%"
    rows = db.execute(
        select(ChatMessage, User.email)
        .join(User, User.id == ChatMessage.user_id, isouter=True)
        .where(or_(func.lower(ChatMessage.question).like(mau),
                   func.lower(ChatMessage.answer).like(mau)))
        .order_by(ChatMessage.id.desc()).limit(limit)).all()

    hits = []
    for msg, email in rows:
        nguon = msg.question if q.lower() in msg.question.lower() else msg.answer
        vi_tri = nguon.lower().find(q.lower())
        dau = max(0, vi_tri - 60)
        hits.append(ChatSearchHit(
            message_id=msg.id, conversation_id=msg.conversation_id, user_id=msg.user_id,
            user_email=email or "(đã xóa)", at=msg.created_at, ticker=msg.ticker,
            snippet=("…" if dau else "") + nguon[dau:vi_tri + 160].strip() + "…"))
    return hits


# ── Thiết bị & chống lạm dụng ────────────────────────────────────────────────

@router.get("/devices", response_model=list[AdminDevice], summary="Vân tay thiết bị")
def list_devices(sort: str = Query("account_count", pattern="^(account_count|last_seen|request_count)$"),
                 blocked: bool | None = Query(None),
                 limit: int = Query(50, ge=1, le=200),
                 db: Session = Depends(get_db)) -> list[AdminDevice]:
    """Xếp mặc định theo SỐ TÀI KHOẢN dùng chung — cột lộ kẻ tạo tài khoản hàng loạt."""
    cot = {"account_count": DeviceFingerprint.account_count,
           "last_seen": DeviceFingerprint.last_seen,
           "request_count": DeviceFingerprint.request_count}[sort]
    query = select(DeviceFingerprint).order_by(cot.desc()).limit(limit)
    if blocked is not None:
        query = query.where(DeviceFingerprint.blocked.is_(blocked))

    devices = list(db.scalars(query).all())
    emails = _emails_theo_thiet_bi(db, [d.fp_hash for d in devices])
    return [AdminDevice.model_validate(d).model_copy(update={"emails": emails.get(d.fp_hash, [])})
            for d in devices]


def _emails_theo_thiet_bi(db: Session, fps: list[str]) -> dict[str, list[str]]:
    if not fps:
        return {}
    rows = db.execute(
        select(DeviceAccount.fp_hash, User.email)
        .join(User, User.id == DeviceAccount.user_id)
        .where(DeviceAccount.fp_hash.in_(fps))).all()
    out: dict[str, list[str]] = {}
    for fp, email in rows:
        out.setdefault(fp, []).append(email)
    return out


@router.post("/devices/{fp_hash}/block", status_code=status.HTTP_204_NO_CONTENT,
             summary="Chặn một thiết bị")
def block_device(fp_hash: str, payload: DeviceBlockIn, request: Request,
                 admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> None:
    _dat_chan(db, admin, request, fp_hash, True, payload.reason)


@router.post("/devices/{fp_hash}/unblock", status_code=status.HTTP_204_NO_CONTENT,
             summary="Bỏ chặn một thiết bị")
def unblock_device(fp_hash: str, request: Request, admin: User = Depends(require_admin),
                   db: Session = Depends(get_db)) -> None:
    _dat_chan(db, admin, request, fp_hash, False, "")


def _dat_chan(db: Session, admin: User, request: Request, fp_hash: str,
              chan: bool, ly_do: str) -> None:
    device = db.get(DeviceFingerprint, fp_hash)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy thiết bị.")
    truoc = {"blocked": device.blocked, "reason": device.blocked_reason}
    device.blocked = chan
    #  Lời nhắn hiện thẳng cho người dùng — hai máy cùng đời có thể trùng vân tay
    #  nên phải cho họ đường liên hệ, đừng chặn câm.
    device.blocked_reason = (ly_do or "Thiết bị này đã bị hạn chế do dấu hiệu lạm dụng. "
                                      "Liên hệ hỗ trợ nếu bạn cho là nhầm.") if chan else ""
    db.commit()
    audit.log(db, admin, "block_device" if chan else "unblock_device", request=request,
              target_type="device", target_id=fp_hash, before=truoc,
              after={"blocked": chan, "reason": device.blocked_reason})


# ── Kho tri thức (RAG) ───────────────────────────────────────────────────────

@router.get("/rag/status", response_model=RagStatusOut, summary="Tình trạng kho tri thức")
def rag_status(db: Session = Depends(get_db)) -> RagStatusOut:
    from app.services.rag import store

    documents, tickers = store.stats(db)
    job = db.scalar(select(IndexJob).order_by(IndexJob.id.desc()))
    dang_chay = bool(job and job.status == "RUNNING")
    if dang_chay and celery_app.AsyncResult(job.task_id).ready():
        dang_chay = False

    cu_nhat = db.scalar(select(func.min(RagDocument.created_at)))
    moi_nhat = db.scalar(select(func.max(RagDocument.created_at)))
    theo_loai = dict(db.execute(
        select(RagDocument.doc_type, func.count()).group_by(RagDocument.doc_type)).all())

    return RagStatusOut(documents=documents, tickers=tickers, running=dang_chay,
                        last_message=(job.message or job.status) if job else "Chưa lập chỉ mục lần nào.",
                        oldest_days=_ngay_truoc(cu_nhat), newest_days=_ngay_truoc(moi_nhat),
                        by_type=theo_loai)


@router.get("/rag/documents", response_model=list[RagDocOut], summary="Tài liệu trong kho")
def rag_documents(ticker: str = Query("", max_length=12), doc_type: str = Query("", max_length=24),
                  limit: int = Query(50, ge=1, le=200),
                  db: Session = Depends(get_db)) -> list[RagDocOut]:
    query = select(RagDocument).order_by(RagDocument.created_at.desc()).limit(limit)
    if ticker:
        query = query.where(RagDocument.ticker == ticker.upper())
    if doc_type:
        query = query.where(RagDocument.doc_type == doc_type)
    return [RagDocOut(id=d.id, ticker=d.ticker, doc_type=d.doc_type, title=d.title,
                      created_at=d.created_at, chars=len(d.content or ""))
            for d in db.scalars(query).all()]


@router.delete("/rag/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Xóa một tài liệu khỏi kho")
def delete_rag_document(doc_id: int, request: Request, admin: User = Depends(require_admin),
                        db: Session = Depends(get_db)) -> None:
    doc = db.get(RagDocument, doc_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tài liệu.")
    truoc = {"ticker": doc.ticker, "doc_type": doc.doc_type, "title": doc.title}
    db.delete(doc)
    db.commit()
    audit.log(db, admin, "delete_rag_document", request=request, target_type="rag_document",
              target_id=doc_id, before=truoc)


# ── Job & hàng đợi ───────────────────────────────────────────────────────────

@router.get("/jobs", response_model=QueueOut, summary="Job nền + độ dài hàng đợi")
def jobs(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)) -> QueueOut:
    rows = db.scalars(select(IndexJob).order_by(IndexJob.id.desc()).limit(limit)).all()
    do_dai, on = 0, True
    try:
        import redis
        client = redis.Redis.from_url(get_settings().celery_broker_url,
                                      socket_timeout=1, socket_connect_timeout=1)
        do_dai = int(client.llen("celery") or 0)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Không đọc được hàng đợi Celery", extra={"error": str(exc)})
        on = False
    return QueueOut(jobs=[JobOut.model_validate(r) for r in rows],
                    queue_length=do_dai, queue_ok=on)


# ── Nguồn dữ liệu ────────────────────────────────────────────────────────────

#  Kết quả thử nguồn được nhớ 60 giây: mỗi lần mở trang mà bắn thật vào cả 5
#  nguồn thì chính trang giám sát lại thành thứ làm nguồn chặn IP của mình.
_probe_cache: dict[str, ProviderOut] = {}
_probe_at: dict[str, float] = {}
_PROBE_TTL = 60.0


def _thu_nguon(name: str) -> ProviderOut:
    from app.services.providers import cafef, dnse, google_news, vci_direct

    def _vci() -> str:
        return f"{len(vci_direct.constituents('VN30'))} mã trong VN30"

    def _dnse() -> str:
        return f"{len(dnse.ohlcv('FPT', days=5))} nến gần nhất"

    def _cafef() -> str:
        tech = cafef.fetch_technical("FPT", max_rows=5)
        return f"giá {tech.price:g} lúc {tech.asof}"

    def _google() -> str:
        return f"{len(google_news.news('FPT', size=3))} tin"

    def _gemini() -> str:
        from app.core.budget import status_snapshot
        if not get_settings().gemini_api_key:
            raise RuntimeError("chưa cấu hình APP_GEMINI_API_KEY")
        snap = status_snapshot()
        return f"quota {snap['used']}/{snap['cap']} ({snap['level']})"

    probes = {"vci": _vci, "dnse": _dnse, "cafef": _cafef,
              "google_news": _google, "gemini": _gemini}
    if name not in probes:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Không có nguồn '{name}'.")

    bat_dau = time.monotonic()
    try:
        detail, ok = probes[name]() or "", True
    except Exception as exc:  # noqa: BLE001 - thử nguồn không được tự ném lỗi
        detail, ok = str(exc)[:200], False
    return ProviderOut(name=name, ok=ok, latency_ms=int((time.monotonic() - bat_dau) * 1000),
                       detail=detail, checked_at=datetime.now(timezone.utc))


@router.get("/providers", response_model=list[ProviderOut], summary="Tình trạng nguồn dữ liệu")
def providers(refresh: bool = Query(False)) -> list[ProviderOut]:
    ten = ["vci", "dnse", "cafef", "google_news", "gemini"]
    out = []
    for name in ten:
        con_moi = (not refresh and name in _probe_cache
                   and time.monotonic() - _probe_at.get(name, 0) < _PROBE_TTL)
        if not con_moi:
            _probe_cache[name] = _thu_nguon(name)
            _probe_at[name] = time.monotonic()
        out.append(_probe_cache[name])
    return out


@router.post("/providers/{name}/probe", response_model=ProviderOut, summary="Thử một nguồn ngay")
def probe_provider(name: str) -> ProviderOut:
    _probe_cache[name] = _thu_nguon(name)
    _probe_at[name] = time.monotonic()
    return _probe_cache[name]


# ── Cache ────────────────────────────────────────────────────────────────────

@router.get("/cache", response_model=CacheReport, summary="Tình trạng cache trong tiến trình")
def cache_report() -> CacheReport:
    from app.api.routes import stocks

    caches = [("phân tích", stocks._cache), ("lịch sử giá", stocks._history_cache),
              ("dữ liệu tab", stocks._detail_cache)]
    return CacheReport(
        caches=[CacheOut(name=ten, size=len(c), maxsize=c.maxsize, ttl_seconds=int(c.ttl))
                for ten, c in caches],
        note=("Cache nằm TRONG tiến trình web. Chạy nhiều worker thì mỗi worker giữ một "
              "bản riêng — số ở đây là của đúng tiến trình vừa trả lời request này, và "
              "nút xóa cũng chỉ xóa bản đó."))


@router.delete("/cache", summary="Xóa cache (cả kho hoặc theo mã)")
def clear_cache(ticker: str = Query("", max_length=12), request: Request = None,  # type: ignore[assignment]
                admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    """Dùng khi nguồn trả số sai và ta muốn ép lấy lại ngay."""
    from app.api.routes import stocks

    code = ticker.upper().strip()
    da_xoa = 0
    for cache in (stocks._cache, stocks._history_cache, stocks._detail_cache):
        if not code:
            da_xoa += len(cache)
            cache.clear()
            continue
        #  Khóa cache là tuple, mã nằm ở một vị trí bất kỳ tùy loại cache.
        keys = [k for k in list(cache.keys()) if code in k]
        for key in keys:
            cache.pop(key, None)
        da_xoa += len(keys)

    audit.log(db, admin, "clear_cache", request=request, target_type="cache",
              target_id=code or "*", after={"removed": da_xoa})
    return {"removed": da_xoa, "ticker": code or "*"}


# ── Thông báo hệ thống ───────────────────────────────────────────────────────

@router.post("/broadcast", response_model=BroadcastOut, summary="Gửi thông báo tới người dùng")
def broadcast(payload: BroadcastIn, request: Request, admin: User = Depends(require_admin),
              db: Session = Depends(get_db)) -> BroadcastOut:
    """Thông báo trong app (chuông ở header). Không gửi email."""
    query = select(User.id).where(User.status == "active")
    if payload.only_verified:
        query = query.where(User.email_verified_at.is_not(None))
    ids = list(db.scalars(query).all())

    db.add_all([Notification(user_id=uid, ticker="", kind="system", message=payload.message)
                for uid in ids])
    db.commit()
    audit.log(db, admin, "broadcast", request=request, target_type="notification",
              after={"sent": len(ids), "message": payload.message})
    return BroadcastOut(sent=len(ids))
