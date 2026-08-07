"""Provider CafeF — CHỈ cung cấp khối kỹ thuật (giá/xu hướng/RSI/thanh khoản).

`pricehistory.ashx` là endpoint JSON công khai duy nhất của CafeF còn hoạt động
ổn định (kiểm chứng 2026-08). Các endpoint cơ bản khác (financereport,
keymetrics, reportfinance...) đã trả 404/302 — ĐỪNG thử lại.

Dùng `GiaDieuChinh` (giá điều chỉnh) để chuỗi giá liền mạch qua chia tách/cổ tức.
"""
from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from app.services.providers.base import ProviderError, TechnicalData, build_technical

_PRICE_URL = "https://cafef.vn/du-lieu/ajax/pagenew/datahistory/pricehistory.ashx"
_USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36")
_PAGE_SIZE = 20  # CafeF ép cứng 20 dòng/trang


def _ssl_context() -> Optional[ssl.SSLContext]:
    """Ưu tiên CA bundle của certifi (image slim/venv hay thiếu CA hệ thống).
    KHÔNG tắt verify."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # pragma: no cover - môi trường không có certifi
        return None


def _get_json(params: dict) -> dict:
    url = f"{_PRICE_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={
        "User-Agent": _USER_AGENT,
        "Referer": "https://cafef.vn/",
        "Accept": "application/json, text/plain, */*",
    })
    try:
        with urllib.request.urlopen(request, timeout=15, context=_ssl_context()) as response:
            return json.loads(response.read().decode("utf-8", "ignore"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ProviderError(f"CafeF không phản hồi: {exc}") from exc


def _to_iso(date_text: str) -> str:
    """dd/mm/yyyy → yyyy-mm-dd."""
    try:
        day, month, year = date_text.split("/")
        return f"{year}-{month}-{day}"
    except ValueError:
        return date_text


def fetch_technical(ticker: str, max_rows: int = 120) -> TechnicalData:
    """Lấy lịch sử giá (phân trang) → khối kỹ thuật. Trả về thứ tự cũ → mới."""
    closes: list[float] = []
    volumes: list[float] = []
    dates: list[str] = []

    for page in range(1, max_rows // _PAGE_SIZE + 2):
        payload = _get_json({"Symbol": ticker, "StartDate": "", "EndDate": "",
                             "PageIndex": page, "PageSize": _PAGE_SIZE})
        block = payload.get("Data") or {}
        rows = block.get("Data") or []
        if not rows:
            break
        for row in rows:
            price = row.get("GiaDieuChinh") or row.get("GiaDongCua")
            if price:
                closes.append(float(price))
                volumes.append(float(row.get("KhoiLuongKhopLenh") or 0))
                dates.append(str(row.get("Ngay", "")))
        if page * _PAGE_SIZE >= int(block.get("TotalCount", 0)) or len(closes) >= max_rows:
            break

    if not closes:
        raise ProviderError(f"CafeF không có dữ liệu giá cho {ticker}")

    closes.reverse()
    volumes.reverse()
    dates.reverse()
    return build_technical(closes, volumes, _to_iso(dates[-1]))
