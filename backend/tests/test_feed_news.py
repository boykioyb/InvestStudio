"""ISSUE-02 · Feed tin trộn nhiều nguồn, ưu tiên tin TƯƠI và chịu lỗi từng nguồn.

Bối cảnh: feed VCI đóng băng ~2025-08 ("tin toàn tin cũ"). Cách sửa là thêm DNSE
làm nguồn tin tươi (endpoint không cần token) bên cạnh Google News + VCI. Các test
này kiểm ở TẦNG service (`feed.fetch_news`), monkeypatch cả 3 provider nên không
chạm mạng — vì thế cũng patch corporate_events/events để tránh HTTP thật (có
backoff sleep) làm test chậm.
"""
from __future__ import annotations

import pytest

from app.services import feed
from app.services.providers import dnse, google_news, vci_direct
from app.services.providers.dnse import DnseError


@pytest.fixture
def _no_events(monkeypatch):
    """Tắt phần sự kiện doanh nghiệp (không thuộc phạm vi test tin) + chặn mạng."""
    monkeypatch.setattr(dnse, "corporate_events", lambda ticker: [])
    monkeypatch.setattr(vci_direct, "events", lambda ticker: [])


def test_tron_3_nguon_khu_trung_lap_va_sap_theo_ngay_giam_dan(monkeypatch, _no_events):
    """DNSE + Google News + VCI → trộn, lọc trùng theo tiêu đề, mới nhất trước.

    'FPT tin A' xuất hiện ở cả DNSE (có link) và VCI (chỉ tiêu đề). DNSE đứng trước
    nên bản GIÀU thông tin (có 'Đọc bài gốc') phải là bản sống sót sau khi khử trùng.
    """
    monkeypatch.setattr(dnse, "news", lambda ticker, limit=30: [
        {"title": "FPT tin A", "date": "2026-09-18", "source": "cafef.vn",
         "link": "https://dnse.example/a"},
    ])
    monkeypatch.setattr(google_news, "news", lambda ticker, size=15: [
        {"title": "FPT tin B", "date": "2026-09-10", "source": "vnexpress",
         "link": "https://gnews.example/b"},
    ])
    monkeypatch.setattr(vci_direct, "news", lambda ticker, days=365, size=50: [
        {"title": "FPT tin A", "date": "2026-09-18"},   # trùng tiêu đề với DNSE
        {"title": "FPT tin C", "date": "2026-08-01"},
    ])

    result = feed.fetch_news("fpt")

    titles = [n.title for n in result.news]
    assert titles == ["FPT tin A", "FPT tin B", "FPT tin C"]  # sắp theo ngày giảm dần
    assert titles.count("FPT tin A") == 1  # đã khử trùng lặp giữa DNSE và VCI

    tin_a = next(n for n in result.news if n.title == "FPT tin A")
    #  Bản DNSE (có link) thắng: phải có nút 'Đọc bài gốc', không phải chỉ link tìm.
    assert any(link.label.startswith("Đọc bài gốc") for link in tin_a.links)


def test_co_tin_tuoi_duoi_48h(monkeypatch, _no_events):
    """Sau khi thêm DNSE, tin mới nhất phải là tin TƯƠI, không đứng ở mốc 2025-08."""
    monkeypatch.setattr(dnse, "news", lambda ticker, limit=30: [
        {"title": "Tin tươi hôm nay", "date": "2026-09-18", "source": "cafef.vn",
         "link": "https://dnse.example/fresh"},
    ])
    monkeypatch.setattr(google_news, "news", lambda ticker, size=15: [])
    monkeypatch.setattr(vci_direct, "news", lambda ticker, days=365, size=50: [
        {"title": "Tin cũ đóng băng", "date": "2025-08-22"},
    ])

    result = feed.fetch_news("FPT")

    assert result.news[0].date == "2026-09-18"  # tin tươi nổi lên đầu


def test_mot_nguon_loi_khong_lam_sap_ca_feed(monkeypatch, _no_events):
    """DNSE timeout/lỗi → vẫn trả tin từ các nguồn còn sống (không ném lỗi)."""
    def _dnse_hong(ticker, limit=30):
        raise DnseError("DNSE timeout")

    monkeypatch.setattr(dnse, "news", _dnse_hong)
    monkeypatch.setattr(google_news, "news", lambda ticker, size=15: [
        {"title": "Tin báo chí", "date": "2026-09-12", "source": "vnexpress",
         "link": "https://gnews.example/x"},
    ])
    monkeypatch.setattr(vci_direct, "news", lambda ticker, days=365, size=50: [
        {"title": "Tin công bố", "date": "2026-09-05"},
    ])

    result = feed.fetch_news("FPT")

    titles = [n.title for n in result.news]
    assert "Tin báo chí" in titles and "Tin công bố" in titles
