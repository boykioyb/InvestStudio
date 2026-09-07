"""Ba khối điểm nhấn của trang chủ: sự kiện sắp tới · tin mới · bảng điểm theo rổ.

NGÂN SÁCH REQUEST là ràng buộc thiết kế chính ở đây (nguồn chỉ cho ~20 req/phút,
mà trang chủ thì ai vào cũng gọi). Vì vậy tuyệt đối KHÔNG quét từng mã trong rổ:

  · Sự kiện : 1 request cho CẢ SÀN (`dnse.upcoming_corporate_actions`) rồi lọc
              theo rổ ở đây. 30 mã vẫn 1 request. Cache 15 phút, dùng chung mọi rổ.
  · Tin     : 1 request cho CẢ RỔ (`dnse.news_many` nhận danh sách `symbols`).
              Cache 15 phút theo rổ.
  · Bảng điểm: ĐẮT — mỗi mã tốn ~4 request VCI (chỉ số + KQKD + LCTT + hồ sơ) vì
              phải chạy đúng mô hình 100 điểm ở `services/scoring.py` (không được
              nhân bản công thức ra chỗ khác). Nên giới hạn ba lớp:
                – chỉ chấm TOP `_LEADERS_UNIVERSE` mã theo vốn hóa của rổ,
                – mỗi lần gọi chỉ chấm MỚI `_LEADERS_PER_CALL` mã và tối đa
                  `_LEADERS_BUDGET` giây → request không bao giờ treo,
                – điểm từng mã cache `_TTL_LEADERS` (60 phút).
              Hệ quả có chủ ý: lần gọi đầu (cache lạnh) bảng điểm chỉ có vài
              dòng, các lần sau đầy dần rồi ổn định. Thà thiếu dòng còn hơn bịa
              điểm hoặc bắn 20 request một lượt.

Mọi khối đều gọi TUẦN TỰ (không thread) và lỗi nguồn thì trả RỖNG — trang chủ đã
xử lý trạng thái trống, còn số liệu bịa thì không sửa được.
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Callable, Optional
from zoneinfo import ZoneInfo

from app.schemas.market import HighlightEvent, HighlightNews, LeaderRow, MarketHighlights
from app.schemas.stock import Level
from app.services import analyzer, screener
from app.services.providers import dnse
from app.services.providers.dnse import DnseError

_ICT = ZoneInfo("Asia/Ho_Chi_Minh")

_TTL_EVENTS = 900.0    # 15 phút — lịch quyền đổi theo ngày, không theo giây
_TTL_NEWS = 900.0      # 15 phút
_TTL_UNIVERSE = 1800.0  # 30 phút — thành phần rổ + vốn hóa gần như không đổi trong phiên
_TTL_LEADERS = 3600.0  # 60 phút — điểm chỉ đổi khi có BCTC mới hoặc giá chạy nhiều

_LEADERS_UNIVERSE = 6   # số mã tối đa được chấm điểm (top vốn hóa của rổ)
_LEADERS_PER_CALL = 2   # số mã chấm MỚI mỗi request (~4 request VCI mỗi mã)
_LEADERS_BUDGET = 6.0   # giây — trần thời gian riêng cho khối bảng điểm
_NEWS_UNIVERSE = 40     # trần số mã gửi kèm 1 POST tin (rổ HOSE có 400+ mã)
_NEWS_FETCH = 60        # số tin thô xin nguồn trước khi lọc theo rổ / lọc trùng

#  Cache dùng chung cho cả module: khóa -> (mốc monotonic, giá trị).
#  Cùng một khuôn với `services/quote.py` và `routes/screener.py` — repo chưa có
#  helper cache dùng chung nào để tái sử dụng.
_cache: dict[str, tuple[float, Any]] = {}


def _cached(key: str, ttl: float, produce: Callable[[], Any]) -> Any:
    """Chạy `produce()` nếu chưa có trong cache hoặc đã hết hạn."""
    if (hit := _cache.get(key)) and time.monotonic() - hit[0] < ttl:
        return hit[1]
    value = produce()
    _cache[key] = (time.monotonic(), value)
    return value


#  ── Phân loại mức độ + nhãn rút gọn (LÀM Ở BACKEND) ─────────────────────────
#  Frontend chỉ tô màu theo `level` và in `kind`; nếu để nó tự đoán từ chuỗi
#  tiếng Việt thì hai nơi sẽ lệch nhau ngay lần nguồn đổi câu chữ.
#  Quy ước: good = cổ đông NHẬN được gì · warn = cần đọc kỹ / có thể pha loãng
#           · bad = dấu hiệu xấu rõ rệt.
_EVENT_RULES: tuple[tuple[tuple[str, ...], str, Level], ...] = (
    (("hủy niêm yết", "đình chỉ", "tạm ngừng giao dịch", "diện kiểm soát",
      "diện cảnh báo", "hạn chế giao dịch"), "Cảnh báo", "bad"),
    (("cổ tức bằng tiền", "cổ tức tiền"), "Cổ tức tiền", "good"),
    (("cổ tức bằng cổ phiếu",), "Cổ tức cổ phiếu", "good"),
    (("thưởng cổ phiếu",), "Thưởng cổ phiếu", "good"),
    (("đhcđ bất thường", "đại hội cổ đông bất thường"), "ĐHCĐ bất thường", "warn"),
    (("lấy ý kiến",), "Lấy ý kiến cổ đông", "warn"),
    (("phát hành thêm", "chào bán", "phát hành riêng lẻ",
      "quyền mua"), "Phát hành thêm", "warn"),
    (("niêm yết thêm",), "Niêm yết thêm", "warn"),
    (("đhcđ thường niên", "đại hội cổ đông thường niên"), "ĐHCĐ thường niên", "warn"),
    (("nội bộ",), "Giao dịch nội bộ", "warn"),
)


def _classify(name: str) -> tuple[str, Level]:
    """(nhãn rút gọn, mức độ) cho một loại sự kiện.

    Không khớp luật nào → giữ nguyên tên nguồn và xếp "warn": sự kiện lạ nghĩa là
    NÊN ĐỌC, chứ không phải mặc định tốt (tô xanh một sự kiện chưa hiểu là nói sai).
    """
    key = (name or "").strip().lower()
    for needles, label, level in _EVENT_RULES:
        if any(needle in key for needle in needles):
            return label, level
    return (name or "").strip() or "Sự kiện", "warn"


def _today() -> str:
    return datetime.now(_ICT).date().isoformat()


def _universe(group: str) -> list[str]:
    """Mã của rổ, XẾP THEO VỐN HÓA GIẢM DẦN (mã lớn được ưu tiên quét).

    Dùng lại `screener.fetch_list` (1 lần cho cả rổ) để không phải tự tính vốn
    hóa lần nữa. Lỗi nguồn → trả rỗng, cả ba khối sẽ rỗng theo.
    """
    def produce() -> list[str]:
        try:
            result = screener.fetch_list(group, "market_cap", "desc")
        except Exception:  # noqa: BLE001 - nguồn lỗi thì trang chủ vẫn phải mở được
            return []
        return [row.symbol for row in result.rows]

    return _cached(f"universe:{group}", _TTL_UNIVERSE, produce)


def _events(symbols: list[str], limit: int) -> list[HighlightEvent]:
    """Sự kiện SẮP TỚI của các mã trong rổ, gần nhất trước."""
    def produce() -> list[dict]:
        try:
            return dnse.upcoming_corporate_actions()
        except DnseError:
            return []

    #  Khóa KHÔNG chứa rổ: feed là của cả sàn nên một request phục vụ mọi rổ.
    rows = _cached("events:all", _TTL_EVENTS, produce)
    in_group = set(symbols)
    today = _today()

    items: list[HighlightEvent] = []
    for row in rows:
        if row["symbol"] not in in_group:
            continue
        #  GDKHQ là mốc chính; thiếu thì lùi về ĐKCC rồi ngày thực hiện.
        date = row.get("exright_date") or row.get("record_date") or row.get("action_date") or ""
        if not date or date < today:  # đã qua thì không còn là "sắp tới"
            continue
        kind, level = _classify(row["name"])
        items.append(HighlightEvent(
            date=date, symbol=row["symbol"], kind=kind,
            detail=(row.get("title") or "").strip(), level=level,
        ))

    items.sort(key=lambda e: (e.date, e.symbol))
    return items[:limit]


def _news(group: str, symbols: list[str], limit: int) -> list[HighlightNews]:
    """Tin mới nhất của rổ — 1 request cho cả danh sách mã."""
    scanned = symbols[:_NEWS_UNIVERSE]

    def produce() -> list[dict]:
        try:
            return dnse.news_many(scanned, limit=_NEWS_FETCH)
        except DnseError:
            return []

    rows = _cached(f"news:{group}", _TTL_NEWS, produce)
    in_group = set(scanned)

    items: list[HighlightNews] = []
    seen: set[str] = set()
    for row in rows:
        title = (row.get("title") or "").strip()
        if not title or title.lower() in seen:
            continue
        #  Nguồn gắn mỗi tin với 1 mã chính + nhiều mã liên quan. Mã chính có thể
        #  NGOÀI rổ (tin ngành nhắc cả mã nhỏ) → lấy mã đầu tiên thuộc rổ để dòng
        #  tin luôn chỉ về đúng mã người xem đang theo.
        symbol = row.get("symbol") or ""
        if symbol not in in_group:
            symbol = next((s for s in (row.get("symbols") or []) if s in in_group), "")
        if not symbol:
            continue
        seen.add(title.lower())
        items.append(HighlightNews(
            symbol=symbol, title=title, date=row.get("date") or "",
            url=(row.get("link") or "") or None,  # nguồn thiếu link → None, không chuỗi rỗng
        ))

    items.sort(key=lambda n: n.date, reverse=True)
    return items[:limit]


def _score(symbol: str) -> Optional[int]:
    """Điểm 100 của một mã, cache 60 phút. None nếu không lấy nổi dữ liệu.

    Gọi `analyzer.analyze` → `scoring.compute_score`: bảng điểm trang chủ và
    trang phân tích PHẢI ra cùng con số, nên không có đường nào khác.
    """
    if (hit := _cache.get(f"score:{symbol}")) and time.monotonic() - hit[0] < _TTL_LEADERS:
        return hit[1]
    try:
        total = analyzer.analyze(symbol).score.total
    except Exception:  # noqa: BLE001 - một mã lỗi không được làm sập bảng điểm
        return None
    _cache[f"score:{symbol}"] = (time.monotonic(), total)
    return total


def _leaders(symbols: list[str], limit: int) -> list[LeaderRow]:
    """Bảng điểm của top mã theo vốn hóa — điểm cao trước.

    Chỉ chấm thêm `_LEADERS_PER_CALL` mã mỗi request và dừng khi hết
    `_LEADERS_BUDGET` giây; phần còn lại để lần gọi sau (điểm đã chấm nằm trong
    cache 60 phút nên bảng đầy dần chứ không chấm lại từ đầu).
    """
    started = time.monotonic()
    fetched = 0
    rows: list[LeaderRow] = []

    for symbol in symbols[:_LEADERS_UNIVERSE]:
        cached = _cache.get(f"score:{symbol}")
        fresh = bool(cached) and time.monotonic() - cached[0] < _TTL_LEADERS
        if not fresh:
            if fetched >= _LEADERS_PER_CALL or time.monotonic() - started > _LEADERS_BUDGET:
                continue  # hết ngân sách của lần gọi này
            fetched += 1
        if (total := _score(symbol)) is not None:
            rows.append(LeaderRow(symbol=symbol, score=total))

    #  Mã dùng làm khóa phụ để hai mã bằng điểm vẫn cho ra đúng một thứ tự.
    rows.sort(key=lambda r: (-r.score, r.symbol))
    return rows[:limit]


def fetch_highlights(group: str, limit: int = 5) -> MarketHighlights:
    """Ba khối điểm nhấn của một rổ. KHÔNG raise: nguồn lỗi thì mảng đó rỗng."""
    group = group.upper().strip()
    symbols = _universe(group)
    return MarketHighlights(
        group=group,
        events=_events(symbols, limit),
        news=_news(group, symbols, limit),
        leaders=_leaders(symbols, limit),
    )
