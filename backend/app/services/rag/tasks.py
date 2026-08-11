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


@celery_app.task(bind=True, name="rag.index_analysis")
def index_analysis_task(self, analysis: dict) -> dict:
    """Nạp kết quả PHÂN TÍCH của một mã vào kho RAG (chạy nền sau khi phân tích).

    Nhận sẵn dữ liệu đã tính (không crawl lại) → chỉ nhúng + upsert. Nhờ vậy
    "phân tích tới đâu, trợ lý biết tới đó", kể cả mã ngoài VN30.
    """
    from app.schemas.stock import StockAnalysis
    from app.services.rag import indexer, store
    from app.services.rag.gemini import GeminiError, embed_texts

    init_db()
    data = StockAnalysis(**analysis)
    doc: store.DocInput = {
        "source_key": f"analysis:{data.ticker}", "doc_type": "analysis", "ticker": data.ticker,
        "title": f"Phân tích {data.ticker} — {data.name}",
        "content": indexer.analysis_text(data),
        "meta": {"score": data.score.total, "name": data.name}, "embedding": [],
    }
    db = SessionLocal()
    try:
        doc["embedding"] = embed_texts([doc["content"]])[0]
        store.upsert_documents(db, [doc])
        return {"indexed": data.ticker}
    except GeminiError as exc:  # thiếu key / lỗi Gemini → bỏ qua, không phá gì
        return {"skipped": str(exc)}
    finally:
        db.close()
