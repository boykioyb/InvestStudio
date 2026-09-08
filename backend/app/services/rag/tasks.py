"""Task Celery: lập chỉ mục RAG chạy nền trong worker.

Ghi tiến độ vào bảng `index_jobs` (bền vững) và cập nhật state Celery (để theo
dõi realtime nếu cần). Worker KHÔNG chạy lifespan của FastAPI nên tự gọi
`init_db()` để chắc bảng đã tồn tại.
"""
from __future__ import annotations

import logging
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


def _bao_email(email: str | None, ticker: str, message: str) -> None:
    """Gửi email cảnh báo. Hỏng thì bỏ qua — thông báo trong app đã tạo rồi,
    không được để hạ tầng thư làm chết cả job quét ngưỡng."""
    if not email:
        return
    from app.core import mailer
    try:
        mailer.send_alert(email, ticker, message)
    except Exception as exc:  # noqa: BLE001
        logging.getLogger("app.alerts").warning(
            "Không gửi được email cảnh báo", extra={"ticker": ticker, "error": str(exc)})


@celery_app.task(name="watchlist.check_alerts")
def check_watchlist_alerts() -> dict:
    """Quét ngưỡng giá/điểm của mọi mã theo dõi → tạo thông báo trong app.

    Giá: 1 request bảng giá cho tất cả mã cần. Điểm: analyze() từng mã (VCI, nhanh).
    Chống spam: chỉ tạo khi CHƯA có thông báo cùng (user, mã, loại) còn chưa đọc.
    """
    from sqlalchemy import select

    from app.models.user import Notification, User, WatchlistItem
    from app.services import analyzer
    from app.services.providers import vci_direct
    from app.services.providers.vci_direct import VciError

    init_db()
    db = SessionLocal()
    created = 0
    try:
        items = list(db.scalars(select(WatchlistItem).where(
            WatchlistItem.target_price.isnot(None) | WatchlistItem.target_score.isnot(None))))
        if not items:
            return {"created": 0, "checked": 0}

        prices: dict[str, float] = {}
        price_tickers = sorted({it.ticker for it in items if it.target_price is not None})
        if price_tickers:
            try:
                for rec in vci_direct.price_board(price_tickers):
                    raw = rec.get("match_price") or rec.get("ref_price")
                    if rec.get("symbol") and raw:
                        prices[rec["symbol"]] = round(float(raw) / 1000, 2)
            except VciError:
                pass

        scores: dict[str, int] = {}
        for ticker in sorted({it.ticker for it in items if it.target_score is not None}):
            try:
                scores[ticker] = analyzer.analyze(ticker).score.total
            except Exception:  # noqa: BLE001 - mã lỗi thì bỏ qua, không chặn cả job
                pass

        #  Tra email một lần cho mọi user liên quan (thay vì mỗi cảnh báo một
        #  truy vấn). Chỉ lấy người ĐÃ xác minh email và còn bật nhận cảnh báo.
        nguoi_nhan: dict[int, str] = dict(db.execute(
            select(User.id, User.email).where(
                User.id.in_({it.user_id for it in items}),
                User.email_verified_at.is_not(None),
                User.alert_email.is_(True),
                User.status == "active")).all())

        def has_unread(user_id: int, ticker: str, kind: str) -> bool:
            return db.scalar(select(Notification).where(
                Notification.user_id == user_id, Notification.ticker == ticker,
                Notification.kind == kind, Notification.is_read.is_(False))) is not None

        for it in items:
            price = prices.get(it.ticker)
            if (it.target_price is not None and price is not None and price >= it.target_price
                    and not has_unread(it.user_id, it.ticker, "price")):
                loi_nhan = f"{it.ticker} đạt {price} nghìn đ (mục tiêu {it.target_price})."
                db.add(Notification(user_id=it.user_id, ticker=it.ticker, kind="price",
                                    message=loi_nhan))
                _bao_email(nguoi_nhan.get(it.user_id), it.ticker, loi_nhan)
                created += 1
            score = scores.get(it.ticker)
            if (it.target_score is not None and score is not None and score >= it.target_score
                    and not has_unread(it.user_id, it.ticker, "score")):
                loi_nhan = (f"{it.ticker} đạt {score}/100 điểm "
                            f"(mục tiêu {int(it.target_score)}).")
                db.add(Notification(user_id=it.user_id, ticker=it.ticker, kind="score",
                                    message=loi_nhan))
                _bao_email(nguoi_nhan.get(it.user_id), it.ticker, loi_nhan)
                created += 1

        db.commit()
        return {"created": created, "checked": len(items)}
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


@celery_app.task(name="usage.flush")
def usage_flush_task() -> dict:
    """Dồn bộ đếm Redis vào `usage_daily` để /admin vẽ được biểu đồ nhiều ngày."""
    from app.services.usage_flush import flush
    return flush()
