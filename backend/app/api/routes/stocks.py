"""Route phân tích cổ phiếu."""
from __future__ import annotations

import json
import queue
import threading
import time
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.schemas.stock import (
    AlertFeed,
    CompanyProfile,
    CorporateActions,
    FinancialStatement,
    MoneyFlow,
    NewsFeed,
    PositionRequest,
    PositionReview,
    PriceHistory,
    RangeKey,
    RatioTable,
    SourceMode,
    StatementKey,
    StockAnalysis,
    StockStats,
    TradingBoard,
)
from app.services import alerts, analyzer, details, feed, history, market, position
from app.services.providers.base import ProviderError

router = APIRouter(prefix="/stocks", tags=["stocks"])

# Cache đơn giản trong tiến trình: crawl khá chậm và dữ liệu chỉ đổi theo phiên.
_cache: dict[tuple, tuple[float, StockAnalysis]] = {}
_history_cache: dict[tuple, tuple[float, PriceHistory]] = {}


def _sse(event: str, data: Any) -> str:
    """Định dạng một sự kiện Server-Sent Events (JSON không chứa xuống dòng thô)."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _index_analysis(result: StockAnalysis) -> None:
    """Đẩy phân tích vừa tính vào kho RAG (chạy nền qua Celery).

    Nhờ vậy "phân tích tới đâu, trợ lý biết tới đó" — kể cả mã ngoài VN30. Chỉ
    chạy khi đã cấu hình Gemini; mọi lỗi ở đây KHÔNG được làm hỏng phản hồi phân tích.
    """
    if not get_settings().gemini_api_key:
        return
    try:
        from app.services.rag.tasks import index_analysis_task
        index_analysis_task.delay(result.model_dump(mode="json"))
    except Exception:  # noqa: BLE001 - broker lỗi cũng không được ảnh hưởng phân tích
        pass


@router.get(
    "/{ticker}",
    response_model=StockAnalysis,
    summary="Phân tích một mã cổ phiếu",
    response_description="Chỉ số, điểm từng tiêu chí, tầm nhìn và quyết định (đã tính sẵn)",
)
def analyze_stock(
    ticker: str = Path(..., min_length=2, max_length=12, description="Mã cổ phiếu, VD: FPT"),
    pos: int = Query(1, ge=0, le=2, description="Vị thế ngành (định tính)"),
    mgmt: int = Query(1, ge=0, le=2, description="Ban lãnh đạo (định tính)"),
    cat: int = Query(1, ge=0, le=2, description="Catalyst (định tính)"),
    pe_sec: Optional[float] = Query(None, gt=0, description="Ghi đè P/E trung bình ngành"),
    pb_fair: Optional[float] = Query(None, gt=0, description="Ghi đè P/B hợp lý"),
    source: SourceMode = Query("auto", description="Nguồn dữ liệu"),
    refresh: bool = Query(False, description="Bỏ qua cache, crawl lại"),
) -> StockAnalysis:
    symbol = ticker.upper().strip()
    if not symbol.isalnum():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Mã cổ phiếu chỉ gồm chữ và số.")

    key = (symbol, pos, mgmt, cat, pe_sec, pb_fair, source)
    ttl = get_settings().cache_ttl_seconds
    if not refresh and (hit := _cache.get(key)) and time.monotonic() - hit[0] < ttl:
        return hit[1]

    try:
        result = analyzer.analyze(symbol, pos=pos, mgmt=mgmt, cat=cat,
                                  pe_sec=pe_sec, pb_fair=pb_fair, source=source)
    except ProviderError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    _cache[key] = (time.monotonic(), result)
    _index_analysis(result)
    return result


@router.get(
    "/{ticker}/stream",
    summary="Phân tích một mã, phát tiến độ theo thời gian thực (SSE)",
    response_description="Luồng sự kiện: progress… rồi result hoặc error",
)
def analyze_stock_stream(
    ticker: str = Path(..., min_length=2, max_length=12),
    pos: int = Query(1, ge=0, le=2),
    mgmt: int = Query(1, ge=0, le=2),
    cat: int = Query(1, ge=0, le=2),
    pe_sec: Optional[float] = Query(None, gt=0),
    pb_fair: Optional[float] = Query(None, gt=0),
    source: SourceMode = Query("auto"),
    refresh: bool = Query(False),
) -> StreamingResponse:
    """Cùng logic với endpoint thường, nhưng đẩy từng bước THẬT ra client.

    Phần trăm phát ra khi một bước bắt đầu chạy — không phải đồng hồ đếm giả.
    Việc crawl chạy ở thread riêng để không chặn vòng lặp sự kiện.
    """
    symbol = ticker.upper().strip()

    def event_stream():
        if not symbol.isalnum():
            yield _sse("error", {"detail": "Mã cổ phiếu chỉ gồm chữ và số."})
            return

        key = (symbol, pos, mgmt, cat, pe_sec, pb_fair, source)
        ttl = get_settings().cache_ttl_seconds
        if not refresh and (hit := _cache.get(key)) and time.monotonic() - hit[0] < ttl:
            yield _sse("progress", {"step": "cache", "label": "Dùng lại kết quả vừa phân tích",
                                    "percent": 100})
            yield _sse("result", hit[1].model_dump(mode="json"))
            return

        events: queue.Queue = queue.Queue()
        outcome: dict = {}

        def worker() -> None:
            try:
                outcome["data"] = analyzer.analyze(
                    symbol, pos=pos, mgmt=mgmt, cat=cat, pe_sec=pe_sec, pb_fair=pb_fair,
                    source=source,
                    on_progress=lambda step, label, percent: events.put(
                        {"step": step, "label": label, "percent": percent}),
                )
            except ProviderError as exc:
                outcome["error"] = str(exc)
            except Exception as exc:  # pragma: no cover - phòng lỗi ngoài dự kiến
                outcome["error"] = f"Lỗi không mong đợi khi phân tích {symbol}: {exc}"
            finally:
                events.put(None)

        threading.Thread(target=worker, daemon=True).start()

        while (event := events.get()) is not None:
            yield _sse("progress", event)

        if "error" in outcome:
            yield _sse("error", {"detail": outcome["error"]})
            return

        _cache[key] = (time.monotonic(), outcome["data"])
        _index_analysis(outcome["data"])
        yield _sse("result", outcome["data"].model_dump(mode="json"))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # tránh proxy gom buffer làm mất tính real-time
        },
    )


@router.get(
    "/{ticker}/history",
    response_model=PriceHistory,
    summary="Lịch sử giá theo khung thời gian",
    response_description="Nến ngày + thống kê nhanh của khung",
)
def stock_history(
    ticker: str = Path(..., min_length=2, max_length=12),
    range: RangeKey = Query("3m", description="Khung: 1m (1 tháng) · 3m (1 quý) · 1y · 3y"),
) -> PriceHistory:
    """Dữ liệu để NGƯỜI DÙNG tự nhìn xu hướng dài hạn và đối chiếu với điểm số.

    Không ảnh hưởng tới việc chấm điểm — bộ chấm luôn dùng cửa sổ 180 ngày cố định.
    """
    symbol = ticker.upper().strip()
    if not symbol.isalnum():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Mã cổ phiếu chỉ gồm chữ và số.")

    key = ("history", symbol, range)
    ttl = get_settings().cache_ttl_seconds
    if (hit := _history_cache.get(key)) and time.monotonic() - hit[0] < ttl:
        return hit[1]

    try:
        result = history.fetch_history(symbol, range)
    except ProviderError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    _history_cache[key] = (time.monotonic(), result)
    return result


#  Cache chung cho dữ liệu chi tiết các tab (hồ sơ, báo cáo, chỉ số).
_detail_cache: dict[tuple, tuple[float, Any]] = {}


def _cached(key: tuple, produce):
    """Chạy `produce()` nếu chưa có trong cache hoặc đã hết hạn."""
    ttl = get_settings().cache_ttl_seconds
    if (hit := _detail_cache.get(key)) and time.monotonic() - hit[0] < ttl:
        return hit[1]
    try:
        value = produce()
    except ProviderError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    _detail_cache[key] = (time.monotonic(), value)
    return value


def _symbol(ticker: str) -> str:
    code = ticker.upper().strip()
    if not code.isalnum():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Mã cổ phiếu chỉ gồm chữ và số.")
    return code


@router.get("/{ticker}/profile", response_model=CompanyProfile,
            summary="Hồ sơ doanh nghiệp")
def stock_profile(ticker: str = Path(..., min_length=2, max_length=12)) -> CompanyProfile:
    code = _symbol(ticker)
    return _cached(("profile", code), lambda: details.fetch_profile(code))


@router.get("/{ticker}/financials", response_model=FinancialStatement,
            summary="Báo cáo tài chính theo năm")
def stock_financials(
    ticker: str = Path(..., min_length=2, max_length=12),
    statement: StatementKey = Query("income", description="income · balance · cashflow"),
) -> FinancialStatement:
    code = _symbol(ticker)
    return _cached(("fin", code, statement), lambda: details.fetch_statement(code, statement))


@router.get("/{ticker}/ratios", response_model=RatioTable,
            summary="Bộ chỉ số tài chính kỳ gần nhất")
def stock_ratios(ticker: str = Path(..., min_length=2, max_length=12)) -> RatioTable:
    code = _symbol(ticker)
    return _cached(("ratios", code), lambda: details.fetch_ratios(code))


@router.get("/{ticker}/board", response_model=TradingBoard,
            summary="Bảng giá phiên hiện tại")
def stock_board(ticker: str = Path(..., min_length=2, max_length=12)) -> TradingBoard:
    code = _symbol(ticker)
    return _cached(("board", code), lambda: market.fetch_board(code))


@router.get("/{ticker}/money-flow", response_model=MoneyFlow,
            summary="Dòng tiền theo ngày (MFI, OBV) + khối ngoại phiên hiện tại")
def stock_money_flow(
    ticker: str = Path(..., min_length=2, max_length=12),
    range: RangeKey = Query("3m"),
) -> MoneyFlow:
    code = _symbol(ticker)
    return _cached(("flow", code, range), lambda: market.fetch_money_flow(code, range))


@router.get("/{ticker}/stats", response_model=StockStats,
            summary="Thống kê giá tự tính theo khung thời gian")
def stock_stats(
    ticker: str = Path(..., min_length=2, max_length=12),
    range: RangeKey = Query("1y"),
) -> StockStats:
    code = _symbol(ticker)
    return _cached(("stats", code, range), lambda: market.fetch_stats(code, range))


@router.get("/{ticker}/news", response_model=NewsFeed,
            summary="Tin công bố và sự kiện doanh nghiệp")
def stock_news(ticker: str = Path(..., min_length=2, max_length=12)) -> NewsFeed:
    code = _symbol(ticker)
    return _cached(("news", code), lambda: feed.fetch_news(code))


@router.get("/{ticker}/corporate-actions", response_model=CorporateActions,
            summary="Cổ tức, phát hành thêm, giao dịch nội bộ")
def stock_corporate_actions(ticker: str = Path(..., min_length=2, max_length=12)) -> CorporateActions:
    code = _symbol(ticker)
    return _cached(("actions", code), lambda: feed.fetch_corporate_actions(code))


@router.post("/{ticker}/position", response_model=PositionReview,
             summary="Đánh giá vị thế đã mua: nên mua thêm, giữ, hay cắt lỗ")
def stock_position(
    payload: PositionRequest,
    ticker: str = Path(..., min_length=2, max_length=12),
) -> PositionReview:
    """Đối chiếu các đợt mua thật của người dùng với điểm số và giá hiện tại.

    KHÔNG cache: dữ liệu phụ thuộc vào các đợt mua người dùng vừa nhập.
    """
    code = _symbol(ticker)
    try:
        return position.review(code, payload)
    except ProviderError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/{ticker}/alerts", response_model=AlertFeed,
            summary="Cảnh báo: sự kiện quyền, biến động bất thường, tin mới")
def stock_alerts(ticker: str = Path(..., min_length=2, max_length=12)) -> AlertFeed:
    """Mỗi cảnh báo ghi rõ mức chắc chắn (số học / đã đo được / chỉ là thông tin).

    KHÔNG dự đoán hướng giá từ tin tức — xem ghi chú trong `services/alerts.py`.
    """
    code = _symbol(ticker)
    return _cached(("alerts", code), lambda: alerts.fetch_alerts(code))
