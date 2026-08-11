"""Lập chỉ mục dữ liệu VN30 + tin tức vào kho vector cho RAG.

Nguồn dữ liệu: ưu tiên **VCI trực tiếp** (`providers/vci_direct.py`) — không qua
vnstock/vnai nên KHÔNG dính trần 20 req/phút và KHÔNG bị giết tiến trình; cả rổ
VN30 (giá + tin) lấy xong trong vài giây. Nếu VCI lỗi (đổi API…) thì tự **quay
về vnstock** (screener/feed) với giãn cách + retry như cũ.

Vòng lặp nằm ở `run_index(...)`; việc chạy nền do Celery lo (xem `tasks.py`).
`deep=True` mới gọi `analyze()` cho điểm số/ROE (vẫn qua vnstock → có giãn cách).
"""
from __future__ import annotations

import time
from typing import Callable, Optional

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.schemas.stock import NewsFeed, ScreenerRow, StockAnalysis
from app.services import analyzer, feed, screener
from app.services.providers import vci_direct
from app.services.providers.base import ProviderError
from app.services.providers.vci_direct import VciError
from app.services.rag import store
from app.services.rag.gemini import embed_texts

Reporter = Callable[[str], None]

#  Dấu hiệu lỗi đã chạm trần nguồn (chỉ còn dùng cho đường vnstock fallback).
_RATE_HINTS = ("rate limit", "giới hạn", "quota", "429", "too many", "tối đa")


def _throttle() -> None:
    time.sleep(get_settings().index_throttle_seconds)


def _looks_rate_limited(exc: Exception) -> bool:
    return any(hint in str(exc).lower() for hint in _RATE_HINTS)


def _with_retry(fn: Callable, report: Reporter, *, tries: int = 3, cooldown: int = 65):
    """Đường vnstock: chạm trần thì nghỉ rồi thử lại (vnai hay giết tiến trình)."""
    for attempt in range(tries):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            if _looks_rate_limited(exc) and attempt < tries - 1:
                report(f"Chạm giới hạn nguồn, nghỉ {cooldown}s rồi thử lại…")
                time.sleep(cooldown)
                continue
            raise


def _fmt(value: Optional[float], unit: str = "") -> str:
    return "không có số liệu" if value is None else f"{value:g}{unit}"


def _summary_text(row: ScreenerRow) -> str:
    """Ảnh chụp thị trường của một mã (từ bảng giá rổ — 0 request thêm mỗi mã)."""
    return "\n".join([
        f"Mã {row.symbol} — {row.name} (sàn {row.exchange}).",
        f"Giá: {_fmt(row.price, ' nghìn đ')}, thay đổi {_fmt(row.change_pct, '%')}.",
        f"Khối lượng khớp: {_fmt(row.volume, ' triệu cp')}, "
        f"giá trị {_fmt(row.value, ' tỷ đồng')}.",
        f"Khối ngoại mua ròng: {_fmt(row.foreign_net, ' tỷ đồng')}.",
        f"Vốn hóa thị trường: {_fmt(row.market_cap, ' tỷ đồng')}.",
    ])


def analysis_text(a: StockAnalysis) -> str:
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


def _news_text_vci(symbol: str, items: list[dict]) -> str:
    parts = [f"Tin tức và sự kiện gần đây của {symbol}:"]
    for it in items[:15]:
        date = f" ({it['date']})" if it.get("date") else ""
        source = f" — {it['source']}" if it.get("source") else ""
        parts.append(f"- {it['title']}{date}{source}")
    return "\n".join(parts)


def _news_text_feed(feed_data: NewsFeed) -> str:
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


def _analysis_doc(symbol: str, name: str, report: Reporter) -> Optional[store.DocInput]:
    try:
        analysis = _with_retry(lambda: analyzer.analyze(symbol), report)
    except ProviderError:
        return None
    return {
        "source_key": f"analysis:{symbol}", "doc_type": "analysis", "ticker": symbol,
        "title": f"Phân tích {symbol} — {name}", "content": analysis_text(analysis),
        "meta": {"score": analysis.score.total, "name": name}, "embedding": [],
    }


def _load_rows(symbols: Optional[list[str]], report: Reporter):
    """Trả (rows, use_vci) với rows = [(mã, tên, ScreenerRow|None)].

    Đường VCI: 1 request lấy rổ + 1 request bảng giá cả rổ; tái dùng
    `screener._row` để giữ nguyên cách quy đổi đơn vị đã kiểm chứng.
    """
    try:
        codes = ([s.upper() for s in symbols] if symbols
                 else vci_direct.constituents("VN30"))
        records = {r["symbol"]: r for r in vci_direct.price_board(codes) if r.get("symbol")}
        directory = vci_direct.symbol_directory()  # tên công ty + sàn (1 request)
        rows = []
        for code in codes:
            info = directory.get(code) or {}
            #  Bù organ_name + exchange để screener._row có tên/sàn thật.
            record = {**(records.get(code) or {"symbol": code}),
                      "organ_name": info.get("name"), "exchange": info.get("exchange")}
            row = screener._row(record)
            rows.append((code, row.name if row else code, row))
        return rows, True
    except VciError as exc:
        report(f"VCI lỗi ({exc}) — quay về vnstock.")
        if symbols:
            return [(c.upper(), c.upper(), None) for c in symbols], False
        listing = _with_retry(
            lambda: screener.fetch_list("VN30", "market_cap", "desc"), report)
        return [(r.symbol, r.name, r) for r in listing.rows], False


def _news_doc_text(symbol: str, use_vci: bool) -> str:
    """Nội dung doc tin cho một mã. Ưu tiên VCI, hỏng thì rơi về vnstock feed."""
    if use_vci:
        try:
            return _news_text_vci(symbol, vci_direct.news(symbol, days=180, size=30))
        except VciError:
            pass
    try:
        return _news_text_feed(feed.fetch_news(symbol))
    except ProviderError:
        return ""


def run_index(symbols: Optional[list[str]], include_news: bool, deep: bool,
              report: Reporter, skip_existing: bool = True) -> str:
    """Chạy trọn một lần lập chỉ mục (đồng bộ). Trả thông điệp kết thúc.

    `skip_existing=True` → bỏ qua mã đã có tin (`news:*`) để chạy lại thì RESUME.
    """
    db = SessionLocal()
    total = 0
    try:
        rows, use_vci = _load_rows(symbols, report)
        done = store.existing_source_keys(db, "news:") if skip_existing else set()
        report(f"Bắt đầu lập chỉ mục {len(rows)} mã "
               f"({'VCI trực tiếp' if use_vci else 'vnstock'}; bỏ qua {len(done)} mã đã có)…")

        for index, (symbol, name, row) in enumerate(rows, start=1):
            if include_news and skip_existing and f"news:{symbol}" in done:
                report(f"Bỏ qua {index}/{len(rows)} {symbol} (đã lập chỉ mục).")
                continue

            docs: list[store.DocInput] = []
            if row is not None:
                docs.append({
                    "source_key": f"summary:{symbol}", "doc_type": "summary", "ticker": symbol,
                    "title": f"Tổng quan {symbol} — {name}", "content": _summary_text(row),
                    "meta": {"name": name}, "embedding": [],
                })
            if deep:
                if (doc := _analysis_doc(symbol, name, report)):
                    docs.append(doc)
                _throttle()  # analyze() vẫn qua vnstock → luôn giãn cách
            if include_news:
                if (text := _news_doc_text(symbol, use_vci)):
                    docs.append({
                        "source_key": f"news:{symbol}", "doc_type": "news", "ticker": symbol,
                        "title": f"Tin tức {symbol}", "content": text,
                        "meta": {"name": name}, "embedding": [],
                    })
                if not use_vci:  # chỉ giãn cách khi phải dùng vnstock
                    _throttle()

            total += _embed_and_store(db, docs)
            report(f"Đã xử lý {index}/{len(rows)} mã ({total} đoạn).")

        done_msg = f"Hoàn tất: {total} đoạn văn bản cho {len(rows)} mã."
        report(done_msg)
        return done_msg
    finally:
        db.close()


def reindex_blocking(symbols: Optional[list[str]] = None, include_news: bool = True,
                     deep: bool = False, skip_existing: bool = True) -> str:
    """Chạy đồng bộ NGAY trong tiến trình hiện tại (CLI --inline; không cần Celery)."""
    return run_index(symbols, include_news, deep, report=print, skip_existing=skip_existing)
