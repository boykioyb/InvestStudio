"""Tin tức và sự kiện doanh nghiệp cho tab Tin tức · Vốn & cổ tức.

Giới hạn đã kiểm chứng ở TẦNG API GỐC (không phải do vnstock làm rớt): endpoint
`iq.vietcap.com.vn/.../v1/news` chỉ trả về newsId, newsTitle, newsImageUrl và
publicDate. Không có URL bài viết, không có nội dung. Endpoint chi tiết theo
newsId trả `data: null`.

Vì vậy không thể dựng link tới bài gốc. Thay vào đó mỗi tin kèm link TÌM KIẾM
theo đúng tiêu đề, và mỗi mã kèm link tới trang công bố thông tin chính thức —
tất cả đều gắn nhãn rõ ràng là "tìm", tuyệt đối không trình bày như bài gốc.
"""
from __future__ import annotations

from typing import Any, Optional
from urllib.parse import quote_plus

from app.schemas.stock import CorporateActions, EventItem, NewsFeed, NewsItem, NewsLink
from app.services.providers.base import ProviderError

_NEWS_NOTE = ("Nguồn dữ liệu chỉ cung cấp TIÊU ĐỀ và ngày công bố — không có URL bài viết. "
              "Các nút bên dưới mỗi tin là link TÌM KIẾM theo đúng tiêu đề, không phải "
              "đường dẫn tới bài gốc.")


def _search_links(ticker: str, title: str) -> list[NewsLink]:
    """Link tìm kiếm theo đúng tiêu đề — cách khả thi duy nhất để người dùng đọc bài."""
    #  Tiêu đề thường đã bắt đầu bằng mã ("FPT: Nghị quyết…") → tránh lặp "FPT FPT:".
    prefix = "" if ticker.lower() in title.lower() else f"{ticker} "
    query = quote_plus(f"{prefix}{title}".strip())
    return [
        NewsLink(label="Tìm trên CafeF", url=f"https://cafef.vn/tim-kiem.chn?keywords={query}"),
        NewsLink(label="Tìm trên Google", url=f"https://www.google.com/search?q={query}"),
    ]


def _disclosure_links(ticker: str) -> list[NewsLink]:
    """Trang công bố thông tin chính thức — nơi có bản gốc đầy đủ."""
    return [
        NewsLink(label=f"Công bố thông tin {ticker} (HOSE)", kind="official",
                 url=f"https://www.hsx.vn/Modules/Listed/Web/SymbolView/{ticker}"),
        NewsLink(label=f"Trang dữ liệu {ticker} (CafeF)", kind="official",
                 url=f"https://cafef.vn/du-lieu/hose/{ticker.lower()}.chn"),
    ]


def _clean(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return fallback if text.lower() in ("", "nan", "none", "nat") else text


def _date(value: Any) -> str:
    return _clean(value)[:10]


def _f(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        number = float(value)
        return None if number != number else number
    except (TypeError, ValueError):
        return None


def _company(ticker: str):
    try:
        from vnstock import Company
    except ImportError as exc:  # pragma: no cover
        raise ProviderError("Chưa cài thư viện vnstock") from exc
    return Company(symbol=ticker.upper().strip(), source="VCI")


def _event_items(frame) -> list[EventItem]:
    if frame is None or len(frame) == 0:
        return []
    items: list[EventItem] = []
    for record in frame.to_dict("records"):
        name = _clean(record.get("event_name_vi") or record.get("event_name_en"))
        if not name:
            continue
        ratio = _f(record.get("exercise_ratio"))
        items.append(EventItem(
            name=name,
            title=_clean(record.get("event_title_vi") or record.get("event_title_en")),
            date=_date(record.get("public_date") or record.get("display_date1")),
            #  Nguồn trả tỷ lệ dạng 0–1 → đổi sang phần trăm cho dễ đọc.
            ratio=round(ratio * 100, 2) if ratio is not None else None,
            value_per_share=_f(record.get("value_per_share")),
            record_date=_date(record.get("record_date")),
            exright_date=_date(record.get("exright_date")),
            payout_date=_date(record.get("payout_date")),
            action=_clean(record.get("action_type_vi")),
        ))
    return sorted(items, key=lambda e: e.date, reverse=True)


def fetch_news(ticker: str) -> NewsFeed:
    """Tin công bố + sự kiện doanh nghiệp gần đây."""
    ticker = ticker.upper().strip()
    company = _company(ticker)

    def safe(getter):
        try:
            return getter()
        except Exception:
            return None

    news: list[NewsItem] = []
    frame = safe(company.news)
    if frame is not None and len(frame):
        for record in frame.to_dict("records"):
            title = _clean(record.get("news_title") or record.get("friendly_title"))
            if title:
                news.append(NewsItem(
                    title=title,
                    date=_date(record.get("public_date")),
                    links=_search_links(ticker, title),
                ))
        news.sort(key=lambda n: n.date, reverse=True)

    events = _event_items(safe(company.events))

    if not news and not events:
        raise ProviderError(f"Không có tin tức hay sự kiện nào cho {ticker}.")

    return NewsFeed(
        ticker=ticker, news=news[:40], events=events[:30],
        disclosure_links=_disclosure_links(ticker), note=_NEWS_NOTE,
    )


def fetch_corporate_actions(ticker: str) -> CorporateActions:
    """Sự kiện liên quan tới vốn và quyền lợi cổ đông, chia theo loại."""
    ticker = ticker.upper().strip()
    try:
        events = _event_items(_company(ticker).events())
    except ProviderError:
        raise
    except Exception as exc:
        raise ProviderError(f"Không lấy được sự kiện doanh nghiệp của {ticker}: {exc}") from exc

    if not events:
        raise ProviderError(f"Không có sự kiện doanh nghiệp nào cho {ticker}.")

    dividends, issues, insider, others = [], [], [], []
    for event in events:
        name = event.name.lower()
        if "cổ tức" in name:
            dividends.append(event)
        elif "phát hành" in name or "niêm yết thêm" in name:
            issues.append(event)
        elif "nội bộ" in name:
            insider.append(event)
        else:
            others.append(event)

    return CorporateActions(
        ticker=ticker,
        dividends=dividends[:20],
        issues=issues[:20],
        insider=insider[:20],
        others=others[:20],
        note=("Giao dịch nội bộ là đăng ký của lãnh đạo/người liên quan — đăng ký "
              "không đồng nghĩa đã thực hiện."),
    )
