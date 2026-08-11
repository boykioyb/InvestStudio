"""Danh sách mã cổ phiếu theo rổ, có sắp xếp — màn hình duyệt mã.

Giới hạn đã kiểm chứng tận nguồn: KHÔNG có endpoint nào trả lịch sử giá theo LÔ
nhiều mã. `Trading.price_history` có trong thư viện và docstring ghi đúng "for a
list of symbols", nhưng cả VCI lẫn KBS đều ném NotImplementedError. Lấy từng mã
thì 30 mã = 30 request, trong khi hạn mức khách chỉ 20 request/phút.

Vì vậy danh sách dựng từ `price_board` — MỘT request cho cả rổ (427 mã HOSE hết
0.4 giây). Đánh đổi: bảng này chỉ có số liệu KHI ĐANG TRONG PHIÊN. Ngoài phiên
nguồn vẫn trả giá tham chiếu / trần / sàn / số cp niêm yết, nên cột Giá và Vốn
hóa vẫn đúng; các cột %, KL, GT, khối ngoại để TRỐNG thay vì bịa số 0.

Sắp xếp làm ở ĐÂY chứ không ở frontend: một bản cài đặt duy nhất thì không thể
lệch nhau — đúng bài học đã rút ra với hàm làm tròn của mô hình chấm điểm.
"""
from __future__ import annotations

from typing import Any, Optional

from app.schemas.stock import (
    ScreenerColumn,
    ScreenerGroup,
    ScreenerList,
    ScreenerRow,
    SessionState,
)
from app.services.providers.base import ProviderError

_BILLION = 1_000_000_000
_MILLION = 1_000_000

#  CẢNH BÁO ĐƠN VỊ — nguồn trộn hai đơn vị trong cùng một bảng, đã đo tận số thô:
#    accumulated_value  → TRIỆU đồng (VIC: 45.627,92 = KL 207.000 × giá 220.100)
#    foreign_*_value    → ĐỒNG       (FPT: 172.585.903.900 = 172,6 tỷ)
#  Chia nhầm 10^9 cho cột đầu thì cả cột GT hiện 0,0.
_VALUE_TO_BILLION = 1_000       # triệu đồng → tỷ đồng
_FOREIGN_TO_BILLION = _BILLION  # đồng → tỷ đồng

#  Chỉ liệt kê rổ đã kiểm chứng gọi được. VNMID · VNSML · VNX50 · VNALL · CAR
#  nguồn trả lỗi nên cố tình KHÔNG đưa vào để người dùng không bấm phải nút chết.
GROUPS: tuple[ScreenerGroup, ...] = (
    ScreenerGroup(key="VN30", label="VN30",
                  hint="30 mã vốn hóa lớn, thanh khoản cao nhất sàn HOSE"),
    ScreenerGroup(key="VN100", label="VN100",
                  hint="100 mã lớn và vừa của HOSE (đã gồm VN30)"),
    ScreenerGroup(key="HNX30", label="HNX30",
                  hint="30 mã tiêu biểu của sàn Hà Nội"),
    ScreenerGroup(key="HOSE", label="Toàn HOSE",
                  hint="Toàn bộ mã đang niêm yết trên HOSE"),
)

#  Metadata cột do máy chủ khai báo: frontend chỉ dựng bảng theo mô tả này,
#  không tự đặt nhãn hay đơn vị — tránh chữ nghĩa hai nơi lệch nhau.
COLUMNS: tuple[ScreenerColumn, ...] = (
    ScreenerColumn(key="symbol", label="Mã", unit="", type="text", digits=0,
                   hint="Mã chứng khoán. Bấm vào dòng để phân tích mã đó."),
    ScreenerColumn(key="name", label="Tên công ty", unit="", type="text", digits=0,
                   hint="Tên đầy đủ của doanh nghiệp niêm yết."),
    ScreenerColumn(key="price", label="Giá", unit="nghìn đ", type="number", digits=2,
                   hint="Giá khớp gần nhất. Ngoài phiên thì là giá tham chiếu, "
                        "tức giá đóng cửa của phiên trước."),
    ScreenerColumn(key="change_pct", label="+/−", unit="%", type="number", digits=2, signed=True,
                   hint="Phần trăm thay đổi so với giá tham chiếu = "
                        "(giá khớp − tham chiếu) / tham chiếu × 100. "
                        "Ngoài phiên để trống vì chưa có giá khớp."),
    ScreenerColumn(key="volume", label="KL", unit="triệu cp", type="number", digits=2,
                   hint="Khối lượng khớp lũy kế từ đầu phiên. Thanh khoản mỏng "
                        "nghĩa là khi cần bán gấp có thể không có người mua."),
    ScreenerColumn(key="value", label="GT", unit="tỷ đồng", type="number", digits=1,
                   hint="Giá trị khớp lũy kế = tổng tiền đã sang tay trong phiên."),
    ScreenerColumn(key="foreign_net", label="NN ròng", unit="tỷ đồng", type="number", digits=2,
                   signed=True,
                   hint="Khối ngoại mua ròng = giá trị nước ngoài mua − bán. "
                        "Dương là họ gom, âm là họ xả. Chỉ của MỘT phiên, "
                        "không phải xu hướng."),  # hint được viết lại theo trạng thái phiên
    ScreenerColumn(key="market_cap", label="Vốn hóa", unit="tỷ đồng", type="number", digits=0,
                   hint="Vốn hóa thị trường = số cổ phiếu niêm yết × giá. "
                        "Cho biết quy mô doanh nghiệp trên sàn."),
)

_COLUMN_BY_KEY = {column.key: column for column in COLUMNS}

#  Hai cột dưới đây có ý nghĩa KHÁC nhau tùy phiên đã khớp lệnh hay chưa, nên
#  lời giải thích phải đổi theo — nói "giá khớp" khi thực ra là giá tham chiếu,
#  hay nói "khối ngoại hôm nay" khi đó là số phiên trước, đều là nói sai.
#  Giá và khối ngoại phụ thuộc HAI dấu hiệu KHÁC nhau, không gộp làm một được:
#  phiên ATO cho ra giá khớp trước khi nguồn cập nhật khối lượng lũy kế, nên
#  "đã có giá khớp" và "đã có khối lượng" là hai chuyện riêng.
_PRICE_HINT = (
    "Giá khớp gần nhất. Mã nào phiên này chưa khớp thì là giá tham chiếu — "
    "giá đóng cửa của phiên gần nhất đã giao dịch.",
    "Phiên này chưa mã nào khớp lệnh nên TOÀN BỘ cột là giá tham chiếu, tức "
    "giá đóng cửa của phiên gần nhất đã giao dịch.",
)
_FOREIGN_HINT = (
    "Khối ngoại mua ròng lũy kế trong phiên đang diễn ra (mua − bán). Dương là "
    "họ gom, âm là họ xả. Đầu phiên con số có thể vẫn là của phiên trước vì "
    "nguồn không xóa khi mở phiên mới.",
    "Khối ngoại mua ròng của PHIÊN GẦN NHẤT ĐÃ GIAO DỊCH, không phải phiên đang "
    "mở. Biết chắc vì có mã ghi khối ngoại lớn hơn cả tổng giá trị đã khớp của "
    "chính nó — điều không thể xảy ra nếu là số của phiên này.",
)


def _columns(matched: bool, fresh_foreign: bool) -> list[ScreenerColumn]:
    """Bộ cột với lời giải thích khớp đúng trạng thái phiên."""
    hints = {
        "price": _PRICE_HINT[0 if matched else 1],
        "foreign_net": _FOREIGN_HINT[0 if fresh_foreign else 1],
    }
    return [
        column.model_copy(update={"hint": hints[column.key]}) if column.key in hints else column
        for column in COLUMNS
    ]

#  Khóa sắp xếp hợp lệ — dùng để chặn tham số bậy ngay ở tầng route.
SORT_KEYS: tuple[str, ...] = tuple(_COLUMN_BY_KEY)

_NOTE = ("Bảng chỉ có số liệu khớp lệnh khi đang trong phiên. Đây là ảnh chụp MỘT "
         "phiên, không phải xu hướng — đừng mua bán chỉ vì một dòng trong bảng.")


def _f(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        number = float(value)
        return None if number != number else number  # loại NaN
    except (TypeError, ValueError):
        return None


def _positive(value: Any) -> Optional[float]:
    """Nguồn dùng 0 để nói 'chưa có số liệu' → quy về None để hiển thị ô trống."""
    number = _f(value)
    return number if number else None


def _price(value: Any) -> Optional[float]:
    """Nguồn trả giá theo ĐỒNG → quy về nghìn đồng cho khớp phần còn lại của app."""
    number = _positive(value)
    return None if number is None else round(number / 1000, 2)


def _clean(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return fallback if text.lower() in ("", "nan", "none") else text


def _flatten(frame) -> list[dict[str, Any]]:
    """Cột MultiIndex ('match', 'match_price') → khóa phẳng 'match_price'."""
    records: list[dict[str, Any]] = []
    for _, record in frame.iterrows():
        row: dict[str, Any] = {}
        for column in frame.columns:
            key = column[-1] if isinstance(column, tuple) else column
            row[str(key)] = record[column]
        records.append(row)
    return records


def _row(record: dict[str, Any]) -> Optional[ScreenerRow]:
    symbol = _clean(record.get("symbol")).upper()
    if not symbol:
        return None

    reference = _price(record.get("ref_price"))
    match = _price(record.get("match_price"))
    #  Ngoài phiên chưa có giá khớp → dùng tham chiếu (đóng cửa phiên trước) để
    #  cột Giá và Vốn hóa vẫn có nghĩa, nhưng %/KL/GT vẫn để trống.
    price = match if match is not None else reference

    change_pct = None
    if match is not None and reference:
        change_pct = round((match - reference) / reference * 100, 2)

    market_cap = None
    shares = _positive(record.get("listed_share"))
    if shares and price:
        #  giá đang là nghìn đ → nhân 1000 về đồng, rồi chia tỷ.
        market_cap = round(shares * price * 1000 / _BILLION)

    volume = _positive(record.get("accumulated_volume"))
    value = _positive(record.get("accumulated_value"))

    foreign_net = None
    foreign_stale = False
    buy = _f(record.get("foreign_buy_value"))
    sell = _f(record.get("foreign_sell_value"))
    if buy is not None and sell is not None and (buy or sell):
        foreign_net = round((buy - sell) / _FOREIGN_TO_BILLION, 2)
        #  Khối ngoại mua (hoặc bán) KHÔNG thể lớn hơn tổng giá trị đã khớp của
        #  chính mã đó. Lớn hơn nghĩa là nguồn còn giữ số của phiên trước —
        #  đã đo: FPT khối ngoại mua 172,6 tỷ trong khi cả mã mới khớp 14,5 tỷ.
        traded_value = (value or 0) * _VALUE_TO_BILLION * _MILLION  # về đồng
        foreign_stale = max(buy, sell) > traded_value

    return ScreenerRow(
        symbol=symbol,
        name=_clean(record.get("organ_name"), symbol),
        exchange=_clean(record.get("exchange"), "—"),
        price=price,
        ref_price=reference,
        change_pct=change_pct,
        volume=round(volume / _MILLION, 2) if volume else None,
        value=round(value / _VALUE_TO_BILLION, 1) if value else None,
        foreign_net=foreign_net,
        foreign_stale=foreign_stale,
        market_cap=market_cap,
    )


def sort_rows(rows: list[ScreenerRow], sort: str, order: str) -> list[ScreenerRow]:
    """Sắp xếp bảng. Công khai vì route dùng lại trên dữ liệu đã cache."""
    reverse = order == "desc"
    if _COLUMN_BY_KEY[sort].type == "text":
        return sorted(rows, key=lambda row: _clean(getattr(row, sort)).upper(), reverse=reverse)

    #  Ô TRỐNG luôn nằm cuối bảng dù sắp tăng hay giảm. Nếu để None lẫn vào giữa,
    #  người đọc sẽ tưởng dữ liệu sai chứ không nghĩ là thiếu.
    #  Mã dùng làm khóa phụ để hai giá trị bằng nhau (hoặc cả cột trống) vẫn cho
    #  ra đúng một thứ tự — không phụ thuộc bảng trước đó nằm trong cache thế nào.
    def rank(row: ScreenerRow) -> tuple[bool, float, str]:
        value = getattr(row, sort)
        if value is None:
            return (True, 0.0, row.symbol)
        return (False, -value if reverse else value, row.symbol)

    return sorted(rows, key=rank)


def fetch_list(group: str, sort: str, order: str) -> ScreenerList:
    """Danh sách mã của một rổ, đã sắp xếp sẵn. Raise ProviderError nếu rỗng."""
    #  Đã CAI vnstock: rổ + bảng giá + tên công ty lấy thẳng VCI (không qua vnai).
    from app.services.providers import vci_direct
    from app.services.providers.vci_direct import VciError

    try:
        symbols = vci_direct.constituents(group)
    except VciError as exc:
        raise ProviderError(f"Không lấy được danh sách mã của rổ {group}: {exc}") from exc

    if not symbols:
        raise ProviderError(f"Rổ {group} không có mã nào.")

    try:
        records = vci_direct.price_board(symbols)
        directory = vci_direct.symbol_directory()  # tên + sàn cho cả rổ (1 request)
    except VciError as exc:
        raise ProviderError(f"Không lấy được bảng giá của rổ {group}: {exc}") from exc

    rows = []
    for record in records:
        info = directory.get(record.get("symbol")) or {}
        enriched = {**record, "organ_name": info.get("name"), "exchange": info.get("exchange")}
        if (row := _row(enriched)):
            rows.append(row)
    if not rows:
        raise ProviderError(f"Rổ {group} không có dòng dữ liệu hợp lệ.")

    #  Trạng thái phiên suy ra TỪ DỮ LIỆU, không so giờ đồng hồ — nghỉ lễ hay sàn
    #  tạm ngừng thì đồng hồ vẫn báo "trong phiên" trong khi bảng rỗng.
    total = len(rows)
    matched = sum(1 for row in rows if row.change_pct is not None)
    traded = sum(1 for row in rows if row.volume)
    #  Cột khối ngoại chỉ đáng tin khi KHÔNG mã nào có con số bất khả thi.
    fresh_foreign = not any(row.foreign_stale for row in rows)

    if not matched:
        note = ("Chưa mã nào khớp lệnh. Cột Giá đang hiển thị GIÁ THAM CHIẾU (đóng cửa "
                "phiên gần nhất); các cột +/−, KL, GT để trống vì nguồn chưa có số liệu "
                "— không phải bằng 0.")
    elif not traded:
        note = (f"{matched}/{total} mã đã có giá khớp, nhưng nguồn chưa cập nhật khối "
                "lượng lũy kế nên cột KL và GT còn trống.")
    else:
        note = f"{matched}/{total} mã đã có giá khớp, {traded}/{total} mã đã có khối lượng."

    session = SessionState(
        live=matched > 0,
        label="Đang trong phiên" if matched else "Ngoài phiên khớp lệnh",
        note=note,
    )

    return ScreenerList(
        group=group,
        groups=list(GROUPS),
        columns=_columns(bool(matched), fresh_foreign),
        sort=sort,
        order=order,  # type: ignore[arg-type]
        count=len(rows),
        session=session,
        rows=sort_rows(rows, sort, order),
        note=_NOTE,
    )
