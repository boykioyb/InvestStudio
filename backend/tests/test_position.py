"""Test quy tắc quyết định vị thế — phần SAI LÀ MẤT TIỀN THẬT của cả dự án.

`position._decide` cố ý BẤT ĐỐI XỨNG: kỷ luật cắt lỗ đứng trước cơ hội mua thêm.
Bộ test này khóa đúng thứ tự đó lại, để một lần refactor "cho gọn" sau này không
âm thầm biến công cụ thành cái nút hợp thức hóa việc bình quân giá xuống.
"""
from __future__ import annotations

import pytest

from app.services.position import _ADD_MIN_SCORE, _CUT_MAX_SCORE, _decide


def quyet_dinh(**kw):
    mac_dinh = dict(total=70, verdict_text="Tốt", stop_breached=False, stop_price=20.0,
                    pnl_pct=5.0, weight_pct=3.0, size_max_pct=8.0, has_price=True)
    mac_dinh.update(kw)
    return _decide(**mac_dinh)


# ── Kỷ luật đứng trước cơ hội ────────────────────────────────────────────────

def test_thung_cat_lo_thi_cat_du_diem_rat_cao():
    """Điểm 95 vẫn phải CẮT nếu đã thủng ngưỡng — đây là bất biến số một."""
    hanh_dong = quyet_dinh(total=95, verdict_text="Xuất sắc", stop_breached=True, pnl_pct=-9.4)
    assert hanh_dong.key == "cut"
    assert hanh_dong.level == "bad"
    assert "cắt lỗ" in hanh_dong.reason.lower()


@pytest.mark.parametrize("diem", [0, 25, _CUT_MAX_SCORE - 1])
def test_diem_duoi_nguong_thi_thoat_dan(diem):
    hanh_dong = quyet_dinh(total=diem, verdict_text="Yếu")
    assert hanh_dong.key == "cut"


def test_ngay_tai_nguong_cat_thi_chua_cat():
    """Ranh giới: `< 50` mới cắt, đúng 50 thì chưa."""
    assert quyet_dinh(total=_CUT_MAX_SCORE, verdict_text="Trung bình").key != "cut"


# ── Chỉ được gợi ý mua thêm trong điều kiện hẹp ──────────────────────────────

def test_du_diem_va_con_du_dia_moi_duoc_mua_them():
    hanh_dong = quyet_dinh(total=_ADD_MIN_SCORE, weight_pct=3.0, size_max_pct=8.0)
    assert hanh_dong.key == "add"
    #  Luôn phải kèm câu chặn tâm lý bình quân giá xuống.
    assert "kéo giá vốn xuống" in hanh_dong.detail


def test_diem_sat_duoi_nguong_mua_them_thi_chi_giu():
    assert quyet_dinh(total=_ADD_MIN_SCORE - 1).key == "hold"


def test_cham_tran_ty_trong_thi_khong_mua_them_du_diem_cao():
    hanh_dong = quyet_dinh(total=90, verdict_text="Xuất sắc", weight_pct=8.0, size_max_pct=8.0)
    assert hanh_dong.key == "hold"
    assert "trần" in hanh_dong.reason.lower()


def test_dang_lo_nhung_chua_thung_thi_van_khong_duoc_khuyen_mua_bua():
    """Lỗ 6% (chưa thủng −8%) + điểm tốt → có thể mua thêm, nhưng phải kèm điều kiện."""
    hanh_dong = quyet_dinh(total=75, pnl_pct=-6.0)
    assert hanh_dong.key == "add"
    assert "nếu chưa từng mua mã này" in hanh_dong.detail.lower()


# ── Thiếu dữ liệu thì không kết luận bừa ─────────────────────────────────────

def test_khong_co_gia_thi_khong_ket_luan():
    hanh_dong = quyet_dinh(has_price=False, stop_breached=True, total=10)
    assert hanh_dong.key == "none"
    assert hanh_dong.level == "warn"


def test_chua_biet_ty_trong_thi_coi_nhu_con_du_dia():
    """`weight_pct=None` = người dùng chưa khai quy mô tài khoản, không phải 'đã đầy'."""
    assert quyet_dinh(total=80, weight_pct=None).key == "add"
