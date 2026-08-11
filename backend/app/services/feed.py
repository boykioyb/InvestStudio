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

_NEWS_NOTE = ("Tin nào có 'Đọc bài gốc' là link tới bản gốc do nguồn cung cấp; các nút "
              "'Tìm trên…' là link TÌM KIẾM theo tiêu đề (dự phòng khi không có bài gốc).")


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


def _event_items(events: list[dict]) -> list[EventItem]:
    """Ánh xạ event dict của vci_direct → EventItem (đã sẵn field khớp)."""
    items: list[EventItem] = []
    for e in events:
        name = _clean(e.get("name"))
        if not name:
            continue
        items.append(EventItem(
            name=name,
            title=_clean(e.get("title")),
            date=_date(e.get("date")),
            ratio=e.get("ratio"),
            value_per_share=e.get("value_per_share"),
            record_date=_date(e.get("record_date")),
            exright_date=_date(e.get("exright_date")),
            payout_date=_date(e.get("payout_date")),
            action=_clean(e.get("action")),
        ))
    return sorted(items, key=lambda e: e.date, reverse=True)


def fetch_news(ticker: str) -> NewsFeed:
    """Tin công bố + sự kiện doanh nghiệp gần đây (lấy thẳng VCI, không qua vnstock)."""
    from app.services.providers import vci_direct
    from app.services.providers.vci_direct import VciError

    ticker = ticker.upper().strip()

    def safe(getter):
        try:
            return getter()
        except VciError:
            return None

    news: list[NewsItem] = []
    for item in (safe(lambda: vci_direct.news(ticker, days=365, size=50)) or []):
        title = _clean(item.get("title"))
        if not title:
            continue
        links: list[NewsLink] = []
        #  VCI có link bài gốc → dùng thẳng; kèm luôn link tìm kiếm dự phòng.
        if item.get("link"):
            links.append(NewsLink(label="Đọc bài gốc", url=item["link"], kind="official"))
        links += _search_links(ticker, title)
        news.append(NewsItem(title=title, date=_date(item.get("date")), links=links))
    news.sort(key=lambda n: n.date, reverse=True)

    events = _event_items(safe(lambda: vci_direct.events(ticker)) or [])

    if not news and not events:
        raise ProviderError(f"Không có tin tức hay sự kiện nào cho {ticker}.")

    return NewsFeed(
        ticker=ticker, news=news[:40], events=events[:30],
        disclosure_links=_disclosure_links(ticker), note=_NEWS_NOTE,
    )


def fetch_corporate_actions(ticker: str) -> CorporateActions:
    """Sự kiện liên quan tới vốn và quyền lợi cổ đông, chia theo loại."""
    from app.services.providers import vci_direct
    from app.services.providers.vci_direct import VciError

    ticker = ticker.upper().strip()
    try:
        events = _event_items(vci_direct.events(ticker))
    except VciError as exc:
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
