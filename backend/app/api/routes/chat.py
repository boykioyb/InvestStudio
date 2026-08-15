"""Route trợ lý RAG: hỏi–đáp, lập chỉ mục (qua Celery), xem trạng thái.

Yêu cầu ĐĂNG NHẬP: hỏi–đáp và lập chỉ mục đều tiêu tốn hạn mức Gemini / nguồn
dữ liệu, nên chỉ mở cho tài khoản đã xác thực. Việc lập chỉ mục KHÔNG chạy trong
web process — nó được đẩy vào hàng đợi Celery cho worker xử lý nền.
"""
from __future__ import annotations

import json
import sys
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core import ratelimit
from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.db.session import get_db
from app.models.rag import ChatMessage, Conversation, IndexJob
from app.models.user import User
from app.schemas.chat import (
    ChatHistoryItem,
    ChatRequest,
    ChatResponse,
    ChatTurnInput,
    Citation,
    ConversationOut,
    ConversationRename,
    IndexStatus,
)
from app.services.rag import agent, store
from app.services.rag.gemini import GeminiError
from app.services.rag.tasks import reindex_task

router = APIRouter(prefix="/chat", tags=["chat"])


def _title_from(question: str) -> str:
    """Tên cuộc trò chuyện tự đặt = câu hỏi đầu, cắt gọn."""
    text = " ".join(question.split())
    return (text[:57] + "…") if len(text) > 60 else text


def _get_conversation(db: Session, user: User, conversation_id: int) -> Conversation:
    conv = db.get(Conversation, conversation_id)
    if conv is None or conv.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cuộc trò chuyện.")
    return conv


def _resolve_conversation(db: Session, user: User, *, conversation_id: Optional[int],
                          start_conversation: bool, question: str,
                          ticker: Optional[str]) -> Optional[Conversation]:
    """Cuộc trò chuyện gắn lượt này. None = tin nhắn phẳng (VD từ widget nổi)."""
    if conversation_id is not None:
        return _get_conversation(db, user, conversation_id)
    if start_conversation:
        conv = Conversation(user_id=user.id, ticker=ticker, title=_title_from(question))
        db.add(conv)
        db.flush()  # lấy id trước khi lưu tin nhắn
        return conv
    return None


def _save_turn(db: Session, user: User, conv: Optional[Conversation], *,
               ticker: Optional[str], question: str, resp: ChatResponse) -> None:
    """Lưu lượt hỏi–đáp + cập nhật thời điểm cuộc trò chuyện (nếu có)."""
    db.add(ChatMessage(user_id=user.id, conversation_id=(conv.id if conv else None),
                       ticker=ticker, question=question, answer=resp.answer,
                       citations=[c.model_dump() for c in resp.citations]))
    if conv is not None:
        conv.updated_at = func.now()
    db.commit()


@router.post("", response_model=ChatResponse, summary="Hỏi trợ lý (RAG) một câu")
def ask(payload: ChatRequest, user: User = Depends(get_current_user),
        db: Session = Depends(get_db)) -> ChatResponse:
    ratelimit.enforce_daily(str(user.id), "rag", get_settings().rag_daily_quota)  # quota/ngày
    ticker = payload.ticker.upper().strip() if payload.ticker else None
    question = payload.question.strip()
    conv = _resolve_conversation(db, user, conversation_id=payload.conversation_id,
                                 start_conversation=payload.start_conversation,
                                 question=question, ticker=ticker)
    try:
        resp = agent.answer_question(db, question, ticker, payload.history)
    except GeminiError as exc:
        #  Không lộ chi tiết lỗi upstream ra client (che thông tin hạ tầng);
        #  ghi log phía máy chủ để còn gỡ lỗi.
        print(f"[chat] GeminiError: {exc}", file=sys.stderr)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Trợ lý tạm thời không phản hồi được. Vui lòng thử lại sau.") from exc

    resp.conversation_id = conv.id if conv else None
    _save_turn(db, user, conv, ticker=ticker, question=question, resp=resp)
    return resp


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _parse_history(raw: Optional[str]) -> list[ChatTurnInput]:
    """Lịch sử hội thoại đi qua query param (SSE là GET) → JSON. Hỏng thì bỏ qua."""
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return [ChatTurnInput(**item) for item in data][-20:]
    except Exception:  # noqa: BLE001 - client gửi rác thì coi như không có lịch sử
        return []


@router.get("/stream", summary="Hỏi trợ lý (RAG) — phát câu trả lời theo luồng (SSE)")
def ask_stream(question: str = Query(..., min_length=3, max_length=1000),
               ticker: Optional[str] = Query(None, max_length=12),
               history: Optional[str] = Query(None, description="JSON các lượt gần nhất"),
               conversation_id: Optional[int] = Query(None),
               start_conversation: bool = Query(False),
               user: User = Depends(get_current_user),
               db: Session = Depends(get_db)) -> StreamingResponse:
    ratelimit.enforce_daily(str(user.id), "rag", get_settings().rag_daily_quota)
    tk = ticker.upper().strip() if ticker else None
    q = question.strip()
    hist = _parse_history(history)
    #  Giải quyết cuộc trò chuyện TRƯỚC khi stream để 'final' mang được id (404 nếu lạ).
    conv = _resolve_conversation(db, user, conversation_id=conversation_id,
                                 start_conversation=start_conversation, question=q, ticker=tk)
    cid = conv.id if conv else None

    def gen():
        final = None
        try:
            for kind, payload in agent.answer_stream(db, q, tk, hist):
                if kind == "delta":
                    yield _sse("delta", {"text": payload})
                elif kind == "step":
                    yield _sse("step", payload)
                else:
                    payload.conversation_id = cid
                    final = payload
                    yield _sse("final", payload.model_dump(mode="json"))
        except GeminiError as exc:
            print(f"[chat] stream GeminiError: {exc}", file=sys.stderr)
            yield _sse("error", {"detail": "Trợ lý tạm thời không phản hồi được. Thử lại sau."})
            return
        #  Lưu lượt hỏi–đáp sau khi stream xong (đủ câu trả lời).
        if final is not None:
            _save_turn(db, user, conv, ticker=tk, question=q, resp=final)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })


@router.get("/history", response_model=list[ChatHistoryItem],
            summary="Lịch sử phẳng (widget nổi) — KHÔNG gồm tin nhắn trong câu chuyện")
def history(ticker: Optional[str] = Query(None, max_length=12,
                                          description="Lọc theo mã (widget nổi); bỏ trống = tất cả"),
            user: User = Depends(get_current_user),
            db: Session = Depends(get_db)) -> list[ChatHistoryItem]:
    #  Chỉ tin nhắn PHẲNG (conversation_id NULL) — câu chuyện dùng endpoint riêng.
    stmt = (select(ChatMessage)
            .where(ChatMessage.user_id == user.id, ChatMessage.conversation_id.is_(None)))
    if ticker:
        stmt = stmt.where(ChatMessage.ticker == ticker.upper().strip())
    rows = list(db.scalars(stmt.order_by(ChatMessage.created_at.desc()).limit(30)))[::-1]
    return [ChatHistoryItem(question=r.question, answer=r.answer,
                            citations=[Citation(**c) for c in (r.citations or [])]) for r in rows]


def _conv_out(conv: Conversation) -> ConversationOut:
    return ConversationOut(id=conv.id, title=conv.title or "(chưa đặt tên)",
                           ticker=conv.ticker, updated_at=conv.updated_at.isoformat())


@router.get("/conversations", response_model=list[ConversationOut],
            summary="Danh sách câu chuyện của người dùng (mới → cũ)")
def list_conversations(user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)) -> list[ConversationOut]:
    rows = db.scalars(select(Conversation).where(Conversation.user_id == user.id)
                      .order_by(Conversation.updated_at.desc()).limit(100))
    return [_conv_out(c) for c in rows]


@router.get("/conversations/{conversation_id}/messages", response_model=list[ChatHistoryItem],
            summary="Các lượt trong một câu chuyện (cũ → mới)")
def conversation_messages(conversation_id: int, user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)) -> list[ChatHistoryItem]:
    _get_conversation(db, user, conversation_id)  # xác thực sở hữu
    rows = db.scalars(select(ChatMessage).where(ChatMessage.conversation_id == conversation_id)
                      .order_by(ChatMessage.created_at.asc()))
    return [ChatHistoryItem(question=r.question, answer=r.answer,
                            citations=[Citation(**c) for c in (r.citations or [])]) for r in rows]


@router.patch("/conversations/{conversation_id}", response_model=ConversationOut,
              summary="Đổi tên câu chuyện")
def rename_conversation(conversation_id: int, payload: ConversationRename,
                        user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)) -> ConversationOut:
    conv = _get_conversation(db, user, conversation_id)
    conv.title = payload.title.strip()
    db.commit()
    return _conv_out(conv)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Xoá câu chuyện (kèm toàn bộ tin nhắn)")
def delete_conversation(conversation_id: int, user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)) -> None:
    conv = _get_conversation(db, user, conversation_id)
    db.delete(conv)  # CASCADE xoá chat_messages con
    db.commit()


def _status(db: Session) -> IndexStatus:
    documents, tickers = store.stats(db)
    job = db.scalar(select(IndexJob).order_by(IndexJob.id.desc()))
    running, message, task_id = False, "Chưa lập chỉ mục lần nào.", None
    if job:
        task_id = job.task_id
        message = job.message or job.status
        running = job.status == "RUNNING"
        #  Worker chết giữa chừng → job kẹt RUNNING; đối chiếu với Celery để không
        #  báo "đang chạy" mãi mãi.
        if running and celery_app.AsyncResult(job.task_id).ready():
            running, message = False, message + " (tiến trình đã kết thúc)"
    return IndexStatus(documents=documents, tickers=tickers, running=running,
                       last_message=message, task_id=task_id)


@router.post("/reindex", response_model=IndexStatus, status_code=status.HTTP_202_ACCEPTED,
             summary="Đưa việc lập chỉ mục VN30 + tin vào hàng đợi (chạy nền qua Celery)")
def reindex(deep: bool = Query(False, description="Kèm điểm số/ROE qua analyze() — chậm hơn"),
            user: User = Depends(get_current_user),
            db: Session = Depends(get_db)) -> IndexStatus:
    current = _status(db)
    if current.running:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            detail="Đang có job lập chỉ mục chạy, vui lòng đợi.")
    try:
        task = reindex_task.delay(None, True, deep)
    except Exception as exc:  # noqa: BLE001 - broker (Redis) không tới được
        print(f"[chat] enqueue reindex thất bại: {exc}", file=sys.stderr)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hệ thống hàng đợi tạm thời không sẵn sàng. Vui lòng thử lại sau.") from exc
    return IndexStatus(documents=current.documents, tickers=current.tickers, running=True,
                       last_message="Đã đưa vào hàng đợi, worker sẽ xử lý…", task_id=task.id)


@router.get("/status", response_model=IndexStatus, summary="Trạng thái kho dữ liệu RAG")
def index_status(user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)) -> IndexStatus:
    return _status(db)
