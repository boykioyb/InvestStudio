"""Cảnh báo: chuyện gì đang/sắp xảy ra với mã này và ảnh hưởng ra sao tới giá.

⚠️ RANH GIỚI QUAN TRỌNG NHẤT CỦA FILE NÀY

Công cụ KHÔNG dự đoán giá lên hay xuống từ tiêu đề tin tức. Nguồn chỉ trả tiêu
đề (0/50 bản ghi có link hay nội dung), nên suy ra hướng giá từ một dòng chữ chỉ
là đoán mò khoác áo phân tích — mà người đọc sẽ đặt lệnh thật theo nó.

Thay vào đó mỗi cảnh báo được gắn một trong ba mức chắc chắn, và mức này phải
hiển thị rõ cho người dùng:

  · mechanical — số học chắc chắn. Ví dụ: ngày giao dịch không hưởng quyền,
                 giá tham chiếu BỊ ĐIỀU CHỈNH giảm đúng bằng giá trị quyền.
                 Đây là quy tắc của sở giao dịch, không phải nhận định.
  · observed   — đã đo được trong dữ liệu quá khứ (khối lượng đột biến, biến
                 động vượt ngưỡng). Là sự thật đã xảy ra, KHÔNG phải dự báo.
  · info       — chỉ là thông tin cần biết. Tuyệt đối không kèm hướng giá.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from app.schemas.stock import Alert, AlertFeed, Level
from app.services import feed, market
from app.services.providers import vnstock_source
from app.services.providers.base import ProviderError

_EFFECT_LABEL = {
    "mechanical": "Tác động số học — chắc chắn xảy ra",
    "observed": "Đã đo được trong dữ liệu — không phải dự báo",
    "info": "Chỉ là thông tin — không suy ra hướng giá",
}

#  Cửa sổ thời gian cho từng loại cảnh báo (ngày).
_EX_UPCOMING_DAYS = 45
_EX_RECENT_DAYS = 20
_ANNOUNCE_DAYS = 30
_INSIDER_DAYS = 45
_NEWS_DAYS = 7

#  Ngưỡng phát hiện bất thường từ dữ liệu giá.
_VOLUME_SPIKE = 2.0     # lần so với trung bình 20 phiên
_SWING_SIGMA = 2.0      # lần độ lệch chuẩn
_NEAR_EXTREME_PCT = 3.0  # % so với đỉnh/đáy khung
_SCAN_SESSIONS = 5       # số phiên gần nhất được soi tìm bất thường


def _today() -> date:
    return date.today()


def _parse(text: str) -> Optional[date]:
    try:
        return datetime.strptime((text or "")[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _alert(key: str, level: Level, title: str, detail: str, kind: str,
           evidence: str = "", when: str = "", rank: int = 50) -> Alert:
    return Alert(
        key=key, level=level, title=title, detail=detail, evidence=evidence,
        effect_kind=kind, effect_label=_EFFECT_LABEL[kind], date=when, rank=rank,
    )


def _corporate_alerts(ticker: str, price: Optional[float]) -> list[Alert]:
    """Sự kiện quyền: đây là nhóm có tác động giá TÍNH ĐƯỢC CHÍNH XÁC."""
    try:
        actions = feed.fetch_corporate_actions(ticker)
    except ProviderError:
        return []

    today = _today()
    result: list[Alert] = []

    for event in actions.dividends + actions.issues:
        ex = _parse(event.exright_date)
        announced = _parse(event.date)
        is_cash = "cổ tức" in event.name.lower()

        if ex:
            delta = (ex - today).days

            #  Sắp tới ngày GDKHQ → báo trước mức điều chỉnh sẽ xảy ra.
            if 0 <= delta <= _EX_UPCOMING_DAYS:
                drop, how = _adjustment(event, is_cash, price)
                result.append(_alert(
                    key="ex_rights_upcoming", level="warn", rank=5,
                    title=f"Còn {delta} ngày tới ngày giao dịch không hưởng quyền",
                    detail=(f"Ngày {event.exright_date}: {event.title or event.name}. "
                            f"{how} Đây là ĐIỀU CHỈNH KỸ THUẬT theo quy định của sở — "
                            "bạn không mất tiền, phần giảm được bù bằng quyền nhận được. "
                            "Mua sau ngày này thì KHÔNG được nhận quyền."),
                    evidence=drop, when=event.exright_date,
                    kind="mechanical",
                ))

            #  Vừa qua ngày GDKHQ → giải thích cú giảm giá cho người mới.
            elif -_EX_RECENT_DAYS <= delta < 0:
                drop, how = _adjustment(event, is_cash, price)
                result.append(_alert(
                    key="ex_rights_recent", level="good", rank=6,
                    title=f"Đã qua ngày không hưởng quyền {abs(delta)} ngày trước",
                    detail=(f"Ngày {event.exright_date}: {event.title or event.name}. {how} "
                            "Nếu bạn thấy giá tụt quanh ngày đó, phần lớn là do điều chỉnh kỹ "
                            "thuật chứ KHÔNG phải doanh nghiệp xấu đi. Đừng bán tháo vì hiểu nhầm."),
                    evidence=drop, when=event.exright_date,
                    kind="mechanical",
                ))
            continue

        #  Đã công bố nhưng chưa có ngày chốt quyền → sẽ tới, chưa biết khi nào.
        if announced and 0 <= (today - announced).days <= _ANNOUNCE_DAYS:
            ratio = f"tỷ lệ {event.ratio}%" if event.ratio else "chưa công bố tỷ lệ"
            result.append(_alert(
                key="action_announced", level="warn", rank=10,
                title="Vừa công bố sự kiện ảnh hưởng tới số lượng cổ phiếu",
                detail=(f"{event.title or event.name} ({ratio}). Chưa có ngày chốt quyền. "
                        "Khi có, giá tham chiếu sẽ được điều chỉnh tương ứng."),
                evidence=f"Công bố ngày {event.date}", when=event.date,
                kind="mechanical",
            ))

    #  Giao dịch nội bộ: thông tin đáng chú ý, nhưng KHÔNG suy ra hướng giá.
    recent_insider = [e for e in actions.insider
                      if (d := _parse(e.date)) and 0 <= (today - d).days <= _INSIDER_DAYS]
    if recent_insider:
        buys = sum(1 for e in recent_insider if e.action == "Mua")
        sells = sum(1 for e in recent_insider if e.action == "Bán")
        result.append(_alert(
            key="insider", level="warn", rank=25,
            title=f"{len(recent_insider)} giao dịch nội bộ trong {_INSIDER_DAYS} ngày qua",
            detail=(f"Người nội bộ đăng ký MUA {buys} lượt, BÁN {sells} lượt. "
                    "Đăng ký KHÔNG đồng nghĩa đã thực hiện, và lý do cá nhân của họ có thể "
                    "chẳng liên quan gì tới triển vọng doanh nghiệp. Hãy đọc như một dữ kiện "
                    "cần tìm hiểu thêm, không phải tín hiệu mua bán."),
            evidence=f"Gần nhất: {recent_insider[0].title or recent_insider[0].name}",
            when=recent_insider[0].date, kind="info",
        ))

    return result


def _adjustment(event, is_cash: bool, price: Optional[float]) -> tuple[str, str]:
    """(bằng chứng, câu diễn giải mức điều chỉnh giá).

    Cổ tức tiền mặt: giá giảm đúng số tiền trả.
    Cổ phiếu thưởng tỷ lệ r: giá mới = giá cũ ÷ (1 + r) vì số cổ phiếu tăng lên.
    """
    if is_cash and event.value_per_share:
        amount = event.value_per_share / 1000  # đồng → nghìn đồng
        pct = f" (~{amount / price * 100:.2f}% giá hiện tại)" if price else ""
        return (f"{event.value_per_share:,.0f} đ/cp",
                f"Giá tham chiếu sẽ giảm khoảng {amount:g} nghìn đ/cp{pct}.")

    if event.ratio:
        ratio = event.ratio / 100
        drop_pct = (1 - 1 / (1 + ratio)) * 100 if ratio > 0 else 0
        return (f"tỷ lệ {event.ratio}%",
                f"Số cổ phiếu tăng {event.ratio}% nên giá tham chiếu giảm khoảng "
                f"{drop_pct:.2f}% để tổng giá trị không đổi.")

    return ("", "Mức điều chỉnh phụ thuộc phương án cụ thể.")


def _price_alerts(ticker: str) -> list[Alert]:
    """Bất thường ĐÃ XẢY RA trong dữ liệu giá — sự thật đo được, không phải dự báo."""
    try:
        candles = vnstock_source.fetch_ohlcv(ticker, 365)
    except ProviderError:
        return []
    if len(candles) < 25:
        return []

    result: list[Alert] = []
    last = candles[-1]

    #  Quét vài phiên gần nhất, không chỉ phiên cuối: một cú đột biến hôm kia
    #  vẫn đáng biết, dù hôm nay giao dịch đã trở lại bình thường.
    recent = range(max(1, len(candles) - _SCAN_SESSIONS), len(candles))

    def avg_volume_before(index: int) -> float:
        window = [c.volume for c in candles[max(0, index - 20):index]]
        return sum(window) / len(window) if window else 0.0

    spikes = [
        (i, candles[i].volume / avg_volume_before(i))
        for i in recent
        if avg_volume_before(i) and candles[i].volume >= avg_volume_before(i) * _VOLUME_SPIKE
    ]
    if spikes:
        i, times = max(spikes, key=lambda x: x[1])
        candle = candles[i]
        ago = len(candles) - 1 - i
        when_text = "phiên gần nhất" if ago == 0 else f"{ago} phiên trước"
        result.append(_alert(
            key="volume_spike", level="warn", rank=15,
            title=f"Khối lượng đột biến ({when_text})",
            detail=(f"Ngày {candle.date} khớp {candle.volume / 1e6:,.2f} triệu cp, gấp "
                    f"{times:.1f} lần trung bình 20 phiên trước đó. Khối lượng lớn bất thường "
                    "thường đi kèm tin tức hoặc dòng tiền lớn vào/ra — nên tìm hiểu nguyên "
                    "nhân trước khi hành động."),
            evidence=f"TB 20 phiên trước đó: {avg_volume_before(i) / 1e6:,.2f} triệu cp",
            when=candle.date, kind="observed",
        ))

    closes = [c.close for c in candles]
    returns = [(closes[i] - closes[i - 1]) / closes[i - 1]
               for i in range(1, len(closes)) if closes[i - 1]]
    if returns:
        mean = sum(returns) / len(returns)
        sigma = (sum((r - mean) ** 2 for r in returns) / len(returns)) ** 0.5
        swings = [
            (i, (closes[i] - closes[i - 1]) / closes[i - 1])
            for i in recent
            if closes[i - 1] and abs((closes[i] - closes[i - 1]) / closes[i - 1]) >= sigma * _SWING_SIGMA
        ]
        if sigma and swings:
            i, change = max(swings, key=lambda x: abs(x[1]))
            ago = len(candles) - 1 - i
            when_text = "Phiên gần nhất" if ago == 0 else f"{ago} phiên trước"
            up = change > 0
            result.append(_alert(
                key="price_swing", level="warn" if up else "bad", rank=12,
                title=(f"Giá biến động mạnh bất thường — {'tăng' if up else 'giảm'} "
                       f"{abs(change) * 100:.2f}% ({when_text.lower()})"),
                detail=(f"Ngày {candles[i].date}, mức thay đổi vượt {_SWING_SIGMA:g} lần độ lệch "
                        f"chuẩn một năm ({sigma * 100:.2f}%/phiên). Kiểm tra tab Tin tức và "
                        "Vốn & cổ tức xem có sự kiện quyền hay công bố nào trùng thời điểm không."),
                evidence=f"Độ lệch chuẩn 1 năm: {sigma * 100:.2f}%/phiên",
                when=candles[i].date, kind="observed",
            ))

    high = max(c.high for c in candles)
    low = min(c.low for c in candles)
    if high and (high - last.close) / high * 100 <= _NEAR_EXTREME_PCT:
        result.append(_alert(
            key="near_high", level="warn", rank=30,
            title="Giá đang sát đỉnh một năm",
            detail=(f"Giá {last.close:g} chỉ cách đỉnh một năm ({high:g}) "
                    f"{(high - last.close) / high * 100:.2f}%. Vùng đỉnh là nơi nhiều người "
                    "chốt lời, cũng là nơi mua đuổi dễ chịu rủi ro nhất."),
            evidence=f"Đỉnh 1 năm: {high:g}", when=last.date, kind="observed",
        ))
    elif low and (last.close - low) / low * 100 <= _NEAR_EXTREME_PCT:
        result.append(_alert(
            key="near_low", level="bad", rank=30,
            title="Giá đang sát đáy một năm",
            detail=(f"Giá {last.close:g} chỉ cách đáy một năm ({low:g}) "
                    f"{(last.close - low) / low * 100:.2f}%. Rẻ so với quá khứ KHÔNG đồng nghĩa "
                    "là rẻ so với giá trị — hãy xem tab Phân tích AI trước khi bắt đáy."),
            evidence=f"Đáy 1 năm: {low:g}", when=last.date, kind="observed",
        ))

    return result


def _board_alerts(ticker: str) -> list[Alert]:
    """Trạng thái phiên hiện tại: chạm trần/sàn."""
    try:
        board = market.fetch_board(ticker)
    except ProviderError:
        return []

    price = board.match_price
    if price is None:
        return []

    if board.ceiling is not None and price >= board.ceiling:
        return [_alert(
            key="at_ceiling", level="warn", rank=8,
            title="Đang khớp giá trần",
            detail=(f"Giá {price:g} chạm trần {board.ceiling:g}. Lệnh mua giá trần có thể "
                    "không khớp được nếu bên bán cạn. Mua đuổi ở trần là rủi ro cao nhất."),
            evidence=f"Trần {board.ceiling:g} · tham chiếu {board.reference:g}",
            when=board.asof[:10], kind="observed",
        )]

    if board.floor is not None and price <= board.floor:
        return [_alert(
            key="at_floor", level="bad", rank=8,
            title="Đang khớp giá sàn",
            detail=(f"Giá {price:g} chạm sàn {board.floor:g}. Nếu đang nắm giữ, có thể "
                    "khó bán vì bên mua cạn. Kiểm tra ngay có tin xấu gì không."),
            evidence=f"Sàn {board.floor:g} · tham chiếu {board.reference:g}",
            when=board.asof[:10], kind="observed",
        )]

    return []


def _news_alert(ticker: str) -> list[Alert]:
    """Đếm tin mới. CỐ Ý không phân tích hướng giá — xem ghi chú đầu file."""
    try:
        news_feed = feed.fetch_news(ticker)
    except ProviderError:
        return []

    today = _today()
    fresh = [n for n in news_feed.news
             if (d := _parse(n.date)) and 0 <= (today - d).days <= _NEWS_DAYS]
    if not fresh:
        return []

    titles = " · ".join(n.title[:60] for n in fresh[:3])
    return [_alert(
        key="fresh_news", level="warn", rank=20,
        title=f"{len(fresh)} tin công bố mới trong {_NEWS_DAYS} ngày",
        detail=(f"{titles}. Công cụ KHÔNG đoán tin này làm giá lên hay xuống — nguồn chỉ "
                "cung cấp tiêu đề, và đoán hướng giá từ một dòng chữ là việc không đáng "
                "tin. Hãy tự đọc nội dung đầy đủ trên trang công bố thông tin của sở."),
        evidence=f"Tin gần nhất: {fresh[0].date}", when=fresh[0].date, kind="info",
    )]


def fetch_alerts(ticker: str) -> AlertFeed:
    """Gom mọi cảnh báo, xếp theo mức ưu tiên."""
    ticker = ticker.upper().strip()

    price: Optional[float] = None
    asof = ""
    try:
        candles = vnstock_source.fetch_ohlcv(ticker, 10)
        if candles:
            price, asof = candles[-1].close, candles[-1].date
    except ProviderError:
        pass

    alerts = (
        _corporate_alerts(ticker, price)
        + _board_alerts(ticker)
        + _price_alerts(ticker)
        + _news_alert(ticker)
    )
    alerts.sort(key=lambda a: (a.rank, a.date))

    if not alerts:
        alerts = [_alert(
            key="quiet", level="good", rank=99,
            title="Không có cảnh báo nào đáng chú ý",
            detail=("Không có sự kiện quyền sắp tới, không có biến động giá hay khối lượng "
                    "bất thường, và không có tin công bố mới trong tuần."),
            when=asof, kind="observed",
        )]

    return AlertFeed(
        ticker=ticker, asof=asof, alerts=alerts,
        note=("Công cụ KHÔNG dự đoán giá lên/xuống từ tin tức. Chỉ những mục ghi "
              "'Tác động số học' mới là chắc chắn; phần còn lại là dữ kiện để bạn tự tìm hiểu."),
    )
