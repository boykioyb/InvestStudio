"""Route trợ lý RAG: hỏi–đáp, lập chỉ mục (qua Celery), xem trạng thái.

Yêu cầu ĐĂNG NHẬP: hỏi–đáp và lập chỉ mục đều tiêu tốn hạn mức Gemini / nguồn
dữ liệu, nên chỉ mở cho tài khoản đã xác thực. Việc lập chỉ mục KHÔNG chạy trong
web process — nó được đẩy vào hàng đợi Celery cho worker xử lý nền.
"""
from __future__ import annotations

import sys

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.celery_app import celery_app
from app.db.session import get_db
from app.models.rag import IndexJob
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse, IndexStatus
from app.services.rag import chat, store
from app.services.rag.gemini import GeminiError
from app.services.rag.tasks import reindex_task

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse, summary="Hỏi trợ lý (RAG) một câu")
def ask(payload: ChatRequest, user: User = Depends(get_current_user),
        db: Session = Depends(get_db)) -> ChatResponse:
    ticker = payload.ticker.upper().strip() if payload.ticker else None
    try:
        return chat.answer_question(db, payload.question.strip(), ticker)
    except GeminiError as exc:
        #  Không lộ chi tiết lỗi upstream ra client (che thông tin hạ tầng);
        #  ghi log phía máy chủ để còn gỡ lỗi.
        print(f"[chat] GeminiError: {exc}", file=sys.stderr)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Trợ lý tạm thời không phản hồi được. Vui lòng thử lại sau.") from exc


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
