"""Task Celery: lập chỉ mục RAG chạy nền trong worker.

Ghi tiến độ vào bảng `index_jobs` (bền vững) và cập nhật state Celery (để theo
dõi realtime nếu cần). Worker KHÔNG chạy lifespan của FastAPI nên tự gọi
`init_db()` để chắc bảng đã tồn tại.
"""
from __future__ import annotations

from typing import Optional

from app.core.celery_app import celery_app
from app.db.session import SessionLocal, init_db
from app.models.rag import IndexJob
from app.services.rag import indexer


@celery_app.task(bind=True, name="rag.reindex")
def reindex_task(self, symbols: Optional[list[str]] = None, include_news: bool = True,
                 deep: bool = False, skip_existing: bool = True) -> dict:
    init_db()
    db = SessionLocal()
    job = IndexJob(task_id=self.request.id, status="RUNNING", message="Đang khởi động…")
    db.add(job)
    db.commit()

    def report(message: str) -> None:
        job.message = message
        db.commit()
        self.update_state(state="PROGRESS", meta={"message": message})

    try:
        final = indexer.run_index(symbols, include_news, deep, report, skip_existing)
        job.status = "DONE"
        job.message = final
        db.commit()
        return {"message": final}
    except Exception as exc:  # pragma: no cover - báo lỗi ra job rồi ném lại cho Celery
        db.rollback()
        job.status = "ERROR"
        job.message = f"Lập chỉ mục dừng do lỗi: {exc}"
        db.commit()
        raise
    finally:
        db.close()
