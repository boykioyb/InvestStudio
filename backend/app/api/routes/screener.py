"""Route danh sách mã cổ phiếu.

Để riêng khỏi `stocks.py` vì router đó bắt `/{ticker}` — mọi đường dẫn thêm vào
sau sẽ bị nuốt thành một mã chứng khoán.

Cache CHỈ theo rổ, không theo tham số sắp xếp: bấm đổi cột không được phép gọi
lại nguồn (hạn mức khách chỉ 20 request/phút). Sắp xếp chạy trên dữ liệu đã cache.
"""
from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Query, status

from app.core.config import get_settings
from app.schemas.stock import ScreenerList, SortOrder
from app.services import screener
from app.services.providers.base import ProviderError

router = APIRouter(prefix="/screener", tags=["screener"])

_GROUP_KEYS = tuple(group.key for group in screener.GROUPS)

#  Chỉ giữ danh sách CHƯA sắp xếp; sắp xếp làm lại sau mỗi lần gọi (rẻ, không ra mạng).
_cache: dict[str, tuple[float, ScreenerList]] = {}


@router.get("", response_model=ScreenerList,
            summary="Danh sách mã theo rổ, sắp xếp theo cột bất kỳ")
def stock_list(
    group: str = Query("VN30", description=f"Rổ cổ phiếu: {' · '.join(_GROUP_KEYS)}"),
    sort: str = Query("market_cap", description=f"Cột sắp xếp: {' · '.join(screener.SORT_KEYS)}. Mặc định vốn hóa vì đây là cột LUÔN có số liệu, kể cả ngoài phiên"),
    order: SortOrder = Query("desc", description="Chiều sắp xếp"),
) -> ScreenerList:
    group = group.upper().strip()
    if group not in _GROUP_KEYS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail=f"Rổ không hợp lệ. Chọn một trong: {', '.join(_GROUP_KEYS)}.")
    if sort not in screener.SORT_KEYS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail=f"Cột sắp xếp không hợp lệ. Chọn một trong: "
                                   f"{', '.join(screener.SORT_KEYS)}.")

    ttl = get_settings().cache_ttl_seconds
    if (hit := _cache.get(group)) and time.monotonic() - hit[0] < ttl:
        cached = hit[1]
        return cached.model_copy(update={
            "sort": sort, "order": order,
            "rows": screener.sort_rows(cached.rows, sort, order),
        })

    try:
        result = screener.fetch_list(group, sort, order)
    except ProviderError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    _cache[group] = (time.monotonic(), result)
    return result
