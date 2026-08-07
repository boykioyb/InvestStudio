"""Test khóa hành vi của NGUỒN SỰ THẬT DUY NHẤT (app/services/scoring.py).

Mục đích: nếu ai đó sửa ngưỡng/công thức ngoài ý muốn, test này phải đỏ.
Chạy: docker compose run --rm backend pytest
"""
from __future__ import annotations

import pytest

from app.schemas.stock import Metrics
from app.services.scoring import _round_half_up, compute_score

# Bộ chỉ số thật của FPT (crawl 2026-08-03) — mốc chuẩn đã đối chiếu thủ công.
FPT = Metrics(
    growth=19.1, roe=18.7, margin=13.9, de=0.47, ocf="+",
    pe=11.6, pe_sec=15.0, pb=2.44, pb_fair=2.0, div=2.02,
    trend="side", vol=7.97, rsi=61.0, pos=1, mgmt=1, cat=1,
)


def test_fpt_reference_total():
    """Mốc chuẩn: FPT = 72/100, chia theo nhóm 35/13/16/8."""
    score = compute_score("FPT", FPT)
    assert score.total == 72
    assert [c.sum for c in score.categories] == [35, 13, 16, 8]
    assert score.verdict.level == "good"


def test_half_up_rounding():
    """Tiêu chí điểm lẻ ở mức 1 phải làm tròn LÊN (2.5 → 3), không phải 2."""
    assert _round_half_up(2.5) == 3
    assert _round_half_up(2.4) == 2
    # P/B mức 1 (ngang giá hợp lý) trên thang 5đ → 3đ
    metrics = FPT.model_copy(update={"pb": 2.0, "pb_fair": 2.0})
    pb_item = next(i for c in compute_score("X", metrics).categories
                   for i in c.items if i.label == "P/B")
    assert pb_item.level == 1 and pb_item.points == 3


def test_missing_metric_scores_zero_and_is_flagged():
    """Chỉ số None → 0đ + available=False, KHÔNG được cho điểm 'miễn phí'."""
    metrics = FPT.model_copy(update={"roe": None, "de": None})
    score = compute_score("X", metrics)
    flagged = {i.label: i for c in score.categories for i in c.items if not i.available}
    assert set(flagged) == {"ROE", "Nợ vay D/E"}
    assert all(i.points == 0 and i.raw == "N/A (chưa lấy được)" for i in flagged.values())


def test_total_never_exceeds_100():
    """Điểm tối đa mọi tiêu chí = đúng 100."""
    best = Metrics(growth=50, roe=25, margin=25, de=0.2, ocf="+",
                   pe=8, pe_sec=15, pb=1.0, pb_fair=2.0, div=6,
                   trend="up", vol=10, rsi=55, pos=2, mgmt=2, cat=2)
    assert compute_score("BEST", best).total == 100


def test_worst_case_scores_zero():
    worst = Metrics(growth=-10, roe=5, margin=2, de=2.0, ocf="-",
                    pe=30, pe_sec=15, pb=5.0, pb_fair=2.0, div=0,
                    trend="down", vol=0.1, rsi=95, pos=0, mgmt=0, cat=0)
    score = compute_score("WORST", worst)
    assert score.total == 0
    assert score.verdict.level == "bad"


@pytest.mark.parametrize("total_metrics,expected_level", [
    (Metrics(pos=2, mgmt=2, cat=2), "bad"),   # chỉ có định tính → điểm thấp
])
def test_verdict_levels(total_metrics, expected_level):
    assert compute_score("X", total_metrics).verdict.level == expected_level


def test_every_item_and_horizon_has_evidence():
    """Mọi tiêu chí và mọi khung thời gian đều phải có giải thích + dẫn chứng."""
    score = compute_score("FPT", FPT, price=71.7)
    items = [i for c in score.categories for i in c.items]
    assert len(items) == 14
    for item in items:
        e = item.explain
        assert e.what and e.how and e.applied
        assert e.scale, f"{item.label} thiếu thang điểm"
        # Dẫn chứng phải nêu đúng số điểm thực nhận
        assert f"{item.points}/{item.max}" in e.applied
    for horizon in score.horizons:
        e = horizon.explain
        assert e.what and e.how and e.applied
        assert f"{horizon.value}/100" in e.applied
        assert horizon.fit in e.applied


def test_scale_text_matches_real_scoring():
    """Thang điểm hiển thị sinh từ CHÍNH band dùng để chấm → không thể lệch."""
    from app.services import criteria
    from app.services.scoring import _points, _scale_text

    for _, _, specs in criteria.GROUPS:
        for spec in specs:
            scale = _scale_text(spec)
            assert len(scale) == len(spec.bands)
            for band, text in zip(spec.bands, scale):
                assert f"{_points(band.level, spec.max)}/{spec.max}đ" in text


def test_horizon_weights_sum_to_one():
    """Trọng số mỗi khung phải cộng đủ 100%, nếu không điểm sẽ sai thang."""
    from app.services.scoring import _HORIZON_SPECS

    for key, spec in _HORIZON_SPECS.items():
        total = sum(weight for _, weight in spec["weights"])
        assert abs(total - 1.0) < 1e-9, f"{key} có tổng trọng số {total}"


def test_group_max_points_sum_to_100():
    from app.services import criteria

    assert sum(maximum for _, maximum, _ in criteria.GROUPS) == 100
    for _, maximum, specs in criteria.GROUPS:
        assert sum(s.max for s in specs) == maximum


def test_missing_metric_explains_it_is_not_a_bad_company():
    """Thiếu dữ liệu phải nói rõ là do chưa lấy được, không phải doanh nghiệp yếu."""
    metrics = FPT.model_copy(update={"roe": None})
    roe = next(i for c in compute_score("X", metrics).categories
               for i in c.items if i.label == "ROE")
    assert not roe.available
    assert "KHÔNG có nghĩa doanh nghiệp yếu" in roe.explain.applied


def test_worst_case_is_concrete_numbers():
    """Kịch bản xấu nhất phải ra SỐ THẬT: giá cắt lỗ và % thiệt hại tài khoản."""
    worst = compute_score("FPT", FPT, price=100.0).decision.worst_case
    assert worst.stop_price == 92.0                    # 100 − 8%
    assert worst.account_loss == "≈ 1.0% tài khoản"    # 12% vị thế × 8% = 0.96 ≈ 1.0
    assert "92" in worst.narrative and "%" in worst.narrative


def test_worst_case_lists_only_real_weaknesses():
    """Chỉ liệt kê tiêu chí bị 0đ của chính mã đó, tối đa 3 mục."""
    metrics = FPT.model_copy(update={"trend": "down", "div": 0.0})
    risks = compute_score("X", metrics, price=50.0).decision.worst_case.risks
    labels = [r.label for r in risks]
    assert "Xu hướng giá" in labels and "Cổ tức" in labels
    assert "ROE" not in labels          # ROE 18.7% đạt điểm tối đa → không phải rủi ro
    assert len(risks) <= 4              # tối đa 3 tiêu chí + 1 mục thiếu dữ liệu


def test_worst_case_flags_missing_data():
    metrics = Metrics(trend="side", vol=8.0, rsi=61.0)
    risks = compute_score("X", metrics, price=20.0).decision.worst_case.risks
    assert any(r.label == "Thiếu dữ liệu" for r in risks)


def test_worst_case_without_price():
    """Không có giá thì không bịa số, nhưng vẫn phải cảnh báo."""
    worst = compute_score("FPT", FPT, price=None).decision.worst_case
    assert worst.stop_price is None
    assert worst.narrative


def test_horizons_present_and_bounded():
    score = compute_score("FPT", FPT)
    assert {h.key for h in score.horizons} == {"short", "mid", "long"}
    assert all(0 <= h.value <= 100 for h in score.horizons)
    assert score.best_horizon.key == max(score.horizons, key=lambda h: h.value).key
