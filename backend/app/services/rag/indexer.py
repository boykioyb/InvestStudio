"""Lập chỉ mục dữ liệu VN30 + tin tức vào kho vector cho RAG.

Vòng lặp lập chỉ mục nằm ở `run_index(...)` — KHÔNG tự quản lý tiến trình. Việc
chạy nền do Celery lo (xem `app/services/rag/tasks.py`); chế độ inline (CLI) gọi
thẳng `reindex_blocking`. Tiến độ báo ra ngoài qua callback `report`.

Ràng buộc cứng: nguồn crawl giới hạn ~20 request/phút. Vì vậy:
  • Tóm tắt VN30 lấy từ `price_board` — MỘT request cho cả rổ.
  • Tin tức: 1 request/mã, có giãn cách (`index_throttle_seconds`).
  • Chạm giới hạn thì TỰ NGHỈ rồi thử lại thay vì chết cả job.
  • `deep=True` mới gọi `analyze()` cho từng mã (nặng request → chậm).
"""
from __future__ import annotations

import time
from typing import Callable, Optional

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.schemas.stock import NewsFeed, ScreenerRow, StockAnalysis
from app.services import analyzer, feed, screener
from app.services.providers.base import ProviderError
from app.services.rag import store
from app.services.rag.gemini import embed_texts

#  Kiểu hàm nhận thông điệp tiến độ (in ra, ghi DB, cập nhật Celery… tùy nơi gọi).
Reporter = Callable[[str], None]

#  Dấu hiệu trong thông điệp lỗi cho biết đã chạm giới hạn nguồn.
_RATE_HINTS = ("rate limit", "giới hạn", "quota", "429", "too many", "tối đa")


def _throttle() -> None:
    time.sleep(get_settings().index_throttle_seconds)


def _looks_rate_limited(exc: Exception) -> bool:
    return any(hint in str(exc).lower() for hint in _RATE_HINTS)


def _with_retry(fn: Callable, report: Reporter, *, tries: int = 3, cooldown: int = 65):
    """Gọi `fn`; chạm giới hạn nguồn thì nghỉ `cooldown` giây rồi thử lại.

    Lỗi KHÔNG phải giới hạn (mã lạ, nguồn hỏng) thì ném ngay để bên gọi bỏ qua mã.
    """
    for attempt in range(tries):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - cần bắt cả lỗi rate-limit của vnai
            if _looks_rate_limited(exc) and attempt < tries - 1:
                report(f"Chạm giới hạn nguồn (20 req/phút), nghỉ {cooldown}s rồi thử lại…")
                time.sleep(cooldown)
                continue
            raise


def _fmt(value: Optional[float], unit: str = "") -> str:
    return "không có số liệu" if value is None else f"{value:g}{unit}"


def _summary_text(row: ScreenerRow) -> str:
    """Ảnh chụp thị trường của một mã (rẻ — dựng từ bảng giá rổ, 0 request thêm)."""
    return "\n".join([
        f"Mã {row.symbol} — {row.name} (sàn {row.exchange}).",
        f"Giá: {_fmt(row.price, ' nghìn đ')}, thay đổi {_fmt(row.change_pct, '%')}.",
        f"Khối lượng khớp: {_fmt(row.volume, ' triệu cp')}, "
        f"giá trị {_fmt(row.value, ' tỷ đồng')}.",
        f"Khối ngoại mua ròng: {_fmt(row.foreign_net, ' tỷ đồng')}.",
        f"Vốn hóa thị trường: {_fmt(row.market_cap, ' tỷ đồng')}.",
    ])


def _analysis_text(a: StockAnalysis) -> str:
    m = a.metrics
    return "\n".join([
        f"Phân tích {a.ticker} — {a.name} (ngành {a.sector}).",
        f"Điểm tổng hợp: {a.score.total}/100 — kết luận: {a.score.verdict.text}.",
        f"ROE (tỷ suất lợi nhuận trên vốn chủ) {_fmt(m.roe, '%')}, "
        f"tăng trưởng LN {_fmt(m.growth, '%')}, biên LN ròng {_fmt(m.margin, '%')}, "
        f"P/E {_fmt(m.pe)}, P/B {_fmt(m.pb)}, D/E {_fmt(m.de)}, "
        f"cổ tức {_fmt(m.div, '%')}, RSI {_fmt(m.rsi)}, xu hướng {m.trend or 'không rõ'}.",
        f"Khuyến nghị hành động (tính sẵn): {a.score.decision.summary}",
    ])


def _news_text(feed_data: NewsFeed) -> str:
    parts = [f"Tin tức và sự kiện gần đây của {feed_data.ticker}:"]
    for item in feed_data.news[:12]:
        parts.append(f"- {item.title}{f' ({item.date})' if item.date else ''}")
    for event in feed_data.events[:12]:
        label = event.title or event.name
        parts.append(f"- [Sự kiện] {label}{f' ({event.date})' if event.date else ''}")
    return "\n".join(parts)


def _embed_and_store(db, docs: list[store.DocInput]) -> int:
    if not docs:
        return 0
    embeddings = embed_texts([doc["content"] for doc in docs])
    for doc, vector in zip(docs, embeddings):
        doc["embedding"] = vector
    return store.upsert_documents(db, docs)


def _news_doc(symbol: str, name: str, report: Reporter) -> Optional[store.DocInput]:
    try:
        news = _with_retry(lambda: feed.fetch_news(symbol), report)
    except ProviderError:
        return None
    return {
        "source_key": f"news:{symbol}", "doc_type": "news", "ticker": symbol,
        "title": f"Tin tức {symbol}", "content": _news_text(news),
        "meta": {"name": name}, "embedding": [],
    }


def _analysis_doc(symbol: str, name: str, report: Reporter) -> Optional[store.DocInput]:
    try:
        analysis = _with_retry(lambda: analyzer.analyze(symbol), report)
    except ProviderError:
        return None
    return {
        "source_key": f"analysis:{symbol}", "doc_type": "analysis", "ticker": symbol,
        "title": f"Phân tích {symbol} — {name}", "content": _analysis_text(analysis),
        "meta": {"score": analysis.score.total, "name": name}, "embedding": [],
    }


def run_index(symbols: Optional[list[str]], include_news: bool, deep: bool,
              report: Reporter, skip_existing: bool = True) -> str:
    """Chạy trọn một lần lập chỉ mục (đồng bộ). Trả thông điệp kết thúc.

    `report(message)` được gọi ở mỗi bước để bên ngoài hiển thị/ghi tiến độ.
    Tự mở/đóng một DB session riêng (an toàn cả trong worker Celery lẫn CLI).

    `skip_existing=True`: bỏ qua mã đã có tin (`news:*`) → chạy lại thì RESUME từ
    chỗ dừng thay vì làm lại từ đầu (quan trọng vì vnai có thể GIẾT tiến trình khi
    chạm trần request, để job dở dang).
    """
    db = SessionLocal()
    total = 0
    try:
        if symbols:
            rows = [(code.upper(), code.upper(), None) for code in symbols]
        else:
            listing = _with_retry(
                lambda: screener.fetch_list("VN30", "market_cap", "desc"), report)
            rows = [(r.symbol, r.name, r) for r in listing.rows]

        done = store.existing_source_keys(db, "news:") if skip_existing else set()
        report(f"Bắt đầu lập chỉ mục {len(rows)} mã (bỏ qua {len(done)} mã đã có)…")
        for index, (symbol, name, row) in enumerate(rows, start=1):
            if include_news and skip_existing and f"news:{symbol}" in done:
                report(f"Bỏ qua {index}/{len(rows)} {symbol} (đã lập chỉ mục).")
                continue
            docs: list[store.DocInput] = []
            if row is not None:  # tóm tắt từ bảng giá rổ — 0 request thêm
                docs.append({
                    "source_key": f"summary:{symbol}", "doc_type": "summary", "ticker": symbol,
                    "title": f"Tổng quan {symbol} — {name}", "content": _summary_text(row),
                    "meta": {"name": name}, "embedding": [],
                })
            if deep:
                if (doc := _analysis_doc(symbol, name, report)):
                    docs.append(doc)
                _throttle()
            if include_news:
                if (doc := _news_doc(symbol, name, report)):
                    docs.append(doc)
                _throttle()

            total += _embed_and_store(db, docs)
            report(f"Đã xử lý {index}/{len(rows)} mã ({total} đoạn).")
        done = f"Hoàn tất: {total} đoạn văn bản cho {len(rows)} mã."
        report(done)
        return done
    finally:
        db.close()


def reindex_blocking(symbols: Optional[list[str]] = None, include_news: bool = True,
                     deep: bool = False, skip_existing: bool = True) -> str:
    """Chạy đồng bộ NGAY trong tiến trình hiện tại (CLI --inline; không cần Celery)."""
    return run_index(symbols, include_news, deep, report=print, skip_existing=skip_existing)
