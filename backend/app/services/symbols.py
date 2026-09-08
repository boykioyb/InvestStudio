"""Gợi ý mã cổ phiếu theo mã, TÊN công ty hoặc TÊN THƯƠNG HIỆU.

Người dùng nhớ "Vietcombank" chứ ít khi nhớ "VCB" — bắt họ nhớ đúng mã là bắt
họ rời trang đi tra Google.

Ba việc đáng nói:

1. **Danh bạ nguồn dùng tên PHÁP LÝ, không phải tên thương hiệu.** VCB đăng ký
   là "Ngân hàng Thương mại Cổ phần Ngoại thương Việt Nam" — không có chữ
   "Vietcombank" nào. Vì vậy có thêm bảng bí danh nhỏ cho những cái tên người
   Việt thật sự gõ. Bảng này ngắn và phải bảo trì tay, đó là cái giá phải trả.
2. **Lọc chứng quyền**: 1.535/3.586 mã trong danh bạ là chứng quyền (CFPT2603…).
   Gõ "FPT" mà nhận về 20 chứng quyền thì ô gợi ý thành vô dụng.
3. **Chuẩn hóa MỘT lần lúc nạp**, không phải mỗi lần gõ phím: bỏ dấu 3.000 cái
   tên cho mỗi ký tự người dùng gõ là lãng phí vô ích.
"""
from __future__ import annotations

import logging
import re
import time
import unicodedata
from dataclasses import dataclass

from app.schemas.stock import SymbolHit

logger = logging.getLogger("app.symbols")

_TTL = 3600.0
#  Chứng quyền có bảo đảm: C + 3 chữ + 4 số. Không phải cổ phiếu, loại khỏi gợi ý.
_CHUNG_QUYEN = re.compile(r"^C[A-Z]{3}\d{4}$")

#  Tên thương hiệu → mã. Chỉ những cái người dùng thật sự gõ; thêm dần khi thấy
#  tìm hụt trong log.
BI_DANH: dict[str, str] = {
    "vietcombank": "VCB", "vcb": "VCB",
    "techcombank": "TCB", "vietinbank": "CTG", "bidv": "BID",
    "vpbank": "VPB", "mbbank": "MBB", "mb bank": "MBB", "acb": "ACB",
    "sacombank": "STB", "hdbank": "HDB", "tpbank": "TPB", "vib": "VIB",
    "shb": "SHB", "seabank": "SSB", "lpbank": "LPB", "ocb": "OCB", "msb": "MSB",
    "eximbank": "EIB", "nam a bank": "NAB", "abbank": "ABB",
    "vingroup": "VIC", "vinhomes": "VHM", "vincom": "VRE", "vinamilk": "VNM",
    "hoa phat": "HPG", "the gioi di dong": "MWG", "dien may xanh": "MWG",
    "fpt": "FPT", "viettel post": "VTP", "sabeco": "SAB", "masan": "MSN",
    "pnj": "PNJ", "petrolimex": "PLX", "pv gas": "GAS", "gas": "GAS",
    "vietjet": "VJC", "vietnam airlines": "HVN", "bao viet": "BVH",
    "ssi": "SSI", "vndirect": "VND", "vps": "VPS", "hcm": "HCM",
    "novaland": "NVL", "khang dien": "KDH", "dat xanh": "DXG", "gelex": "GEX",
    "refrigeration": "REE", "ree": "REE", "the gioi so": "DGW",
}


@dataclass(frozen=True, slots=True)
class _Muc:
    symbol: str
    name: str
    exchange: str
    name_norm: str


_index: list[_Muc] = []
#  Tra theo mã dựng SẴN lúc nạp: dựng lại dict 2.000 mục cho mỗi ký tự người
#  dùng gõ là việc thừa, và ô gợi ý là nơi gõ nhiều nhất trong cả sản phẩm.
_theo_ma: dict[str, _Muc] = {}
_index_at: float = 0.0


def reset_cache() -> None:
    """Xóa danh bạ đang nhớ. Hai biến cache phải luôn được dọn CÙNG nhau —
    tách ra thành hàm để không nơi nào dọn thiếu một nửa rồi tra trúng dữ liệu cũ."""
    global _index, _theo_ma, _index_at
    _index, _theo_ma, _index_at = [], {}, 0.0


def _khong_dau(text: str) -> str:
    """Bỏ dấu tiếng Việt để gõ 'ngan hang' vẫn khớp 'Ngân hàng'."""
    tach = unicodedata.normalize("NFD", (text or "").lower().replace("đ", "d"))
    return "".join(c for c in tach if unicodedata.category(c) != "Mn")


def _danh_ba() -> list[_Muc]:
    global _index, _theo_ma, _index_at
    if _index and time.monotonic() - _index_at < _TTL:
        return _index

    from app.services.providers import vci_direct
    from app.services.providers.vci_direct import VciError
    try:
        raw = vci_direct.symbol_directory()
    except VciError as exc:
        #  Nguồn hỏng → giữ danh bạ cũ nếu có. Ô tìm kiếm vẫn gõ tay được, chỉ
        #  mất phần gợi ý; không được để cả trang chết vì một tính năng phụ.
        logger.warning("Không tải được danh bạ mã", extra={"error": str(exc)})
        return _index

    _index = [
        _Muc(symbol=sym, name=info.get("name", ""), exchange=info.get("exchange", ""),
             name_norm=_khong_dau(info.get("name", "")))
        for sym, info in raw.items()
        if sym and not _CHUNG_QUYEN.match(sym)
    ]
    _theo_ma = {m.symbol: m for m in _index}
    _index_at = time.monotonic()
    logger.info("Đã nạp danh bạ mã", extra={"count": len(_index), "raw": len(raw)})
    return _index


def search(query: str, limit: int = 8) -> list[SymbolHit]:
    """Ưu tiên: trùng mã → bí danh thương hiệu → mã bắt đầu bằng → tên chứa."""
    q = (query or "").strip()
    if not q:
        return []
    q_ma = q.upper()
    q_ten = _khong_dau(q)
    danh_ba = _danh_ba()

    thu_tu: list[_Muc] = []
    da_co: set[str] = set()

    def them(m: _Muc | None) -> None:
        if m and m.symbol not in da_co:
            da_co.add(m.symbol)
            thu_tu.append(m)

    them(_theo_ma.get(q_ma))
    #  Khớp bí danh theo TIỀN TỐ: người dùng gõ tới đâu gợi ý tới đó, không đợi
    #  gõ hết "vietcombank" mới ra VCB.
    for bi_danh, ma in BI_DANH.items():
        if bi_danh.startswith(q_ten):
            them(_theo_ma.get(ma))

    #  Quét toàn bộ danh bạ (~2.000 mục sau khi lọc chứng quyền) — đủ nhanh cho
    #  mỗi lần gõ, và không bỏ sót mục nằm cuối bảng chữ cái như cách cắt sớm.
    batdau = sorted((m for m in danh_ba if m.symbol.startswith(q_ma)),
                    key=lambda m: (len(m.symbol), m.symbol))
    trong_ten = sorted((m for m in danh_ba if q_ten and q_ten in m.name_norm),
                       key=lambda m: (len(m.symbol), m.symbol))
    for m in batdau + trong_ten:
        them(m)
        if len(thu_tu) >= limit:
            break

    return [SymbolHit(symbol=m.symbol, name=m.name, exchange=m.exchange)
            for m in thu_tu[:limit]]
