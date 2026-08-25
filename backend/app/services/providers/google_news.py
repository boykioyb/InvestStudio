"""Nguồn tin thứ 2 — Google News RSS, theo từng mã, KÈM link bài gốc thật.

Vì sao có file này: feed `iq.vietcap.com.vn/.../v1/news` của VCI đã ĐÓNG BĂNG (đo
2026-08-15: mã VIB không có tin nào sau 2025-08-22 dù cửa sổ hỏi tới hôm nay).
VCI cũng chỉ trả tiêu đề, không có URL bài viết. Google News RSS bù đắp cả hai:
tin cập nhật từng ngày, kèm nguồn báo + link bài gốc (link redirect của Google,
mở ra là tới bài thật).

Query: `"<MÃ>" (cổ phiếu OR chứng khoán)` — đo thực tế cho VIB/FPT/HPG đều ra tin
đúng mã, tươi trong ngày. Ràng "cổ phiếu/chứng khoán" để lọc nhiễu khi mã trùng
từ thông thường.

Endpoint:
  · GET news.google.com/rss/search?q=<query>&hl=vi&gl=VN&ceid=VN:vi
"""
from __future__ import annotations

import time
from email.utils import parsedate_to_datetime
from typing import Optional
from urllib.parse import quote_plus
from xml.etree import ElementTree as ET

import httpx

_RSS = "https://news.google.com/rss/search"

_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


class GoogleNewsError(RuntimeError):
    """Lỗi khi lấy Google News RSS (mạng, RSS hỏng). Tách khỏi ProviderError của app."""


_client = httpx.Client(headers=_HEADERS, timeout=20.0, follow_redirects=True)


def _pub_date(raw: str) -> str:
    """RFC-822 pubDate → 'YYYY-MM-DD' (rỗng nếu không parse được)."""
    try:
        return parsedate_to_datetime(raw).date().isoformat()
    except (TypeError, ValueError):
        return (raw or "")[:10]


def _strip_source(title: str, source: str) -> str:
    """Google gắn ' - <Nguồn>' ở đuôi tiêu đề → bỏ đi cho gọn (chỉ khi khớp đúng)."""
    suffix = f" - {source}"
    return title[: -len(suffix)] if source and title.endswith(suffix) else title


def news(ticker: str, size: int = 15) -> list[dict]:
    """Tin báo chí về một mã, mới nhất trước. Mỗi tin: {title, date, source, link}."""
    query = quote_plus(f'"{ticker.upper()}" (cổ phiếu OR chứng khoán)')
    url = f"{_RSS}?q={query}&hl=vi&gl=VN&ceid=VN:vi"

    last = ""
    body: Optional[str] = None
    for attempt in range(3):
        try:
            resp = _client.get(url)
        except httpx.HTTPError as exc:
            last = str(exc)
            time.sleep(1.0 * (attempt + 1))
            continue
        if resp.status_code == 200:
            body = resp.text
            break
        if resp.status_code == 429 or resp.status_code >= 500:
            last = f"HTTP {resp.status_code}"
            time.sleep(1.5 * (attempt + 1))
            continue
        raise GoogleNewsError(f"Google News {resp.status_code}: {resp.text[:150]}")
    if body is None:
        raise GoogleNewsError(f"Google News không phản hồi sau nhiều lần thử: {last}")

    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise GoogleNewsError(f"RSS Google News hỏng: {exc}") from exc

    items: list[dict] = []
    for it in root.findall(".//item")[:size]:
        title = (it.findtext("title") or "").strip()
        if not title:
            continue
        src_el = it.find("source")
        source = (src_el.text or "").strip() if src_el is not None else ""
        items.append({
            "title": _strip_source(title, source),
            "date": _pub_date((it.findtext("pubDate") or "").strip()),
            "source": source,
            "link": (it.findtext("link") or "").strip(),
        })
    return items
