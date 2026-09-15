"""Đồng bộ danh mục từ extension: tạo token, import bằng token, đọc lại, lưu đè."""
from __future__ import annotations


def _register(client, email="hoa@invest.vn"):
    return client.post("/api/auth/register",
                       json={"email": email, "password": "matkhau-dai-hon"})


def _login(client, email="hoa@invest.vn"):
    return client.post("/api/auth/login",
                       json={"email": email, "password": "matkhau-dai-hon"})


def test_import_requires_auth(client):
    #  Không cookie, không token đồng bộ → 401.
    r = client.post("/api/portfolio/import",
                    json={"holdings": [{"ticker": "FPT", "qty": 100}]})
    assert r.status_code == 401, r.text
    assert client.get("/api/portfolio/holdings").status_code == 401


def test_import_token_then_import_and_read(client):
    assert _register(client).status_code == 201
    tok = client.post("/api/portfolio/import-token")
    assert tok.status_code == 200, tok.text
    token = tok.json()["token"]
    assert tok.json()["expires_days"] == 30

    #  Bỏ cookie phiên → buộc dùng ĐÚNG token đồng bộ (giống extension gọi từ xa).
    client.cookies.clear()
    body = {
        "source": "TCBS", "account": "0001M18951",
        "holdings": [
            {"ticker": "tpb", "qty": 1200, "avgPrice": 14544, "marketPrice": 14450},
            {"ticker": "VIB", "qty": 438, "avgPrice": 13428, "marketPrice": 13700},
        ],
        "realized": [
            {"ticker": "TPB", "actualPnl": -2391, "sellQtty": 100},
            {"ticker": "HPG", "actualPnl": 150000, "sellQtty": 200},  # đã bán hết, không còn giữ
        ],
    }
    imp = client.post("/api/portfolio/import", json=body,
                      headers={"Authorization": f"Bearer {token}"})
    assert imp.status_code == 200, imp.text
    assert imp.json()["imported"] == 2          # chỉ đếm mã đang nắm giữ
    assert imp.json()["tickers"] == ["TPB", "VIB"]  # chuẩn hóa hoa + sắp xếp

    #  Đọc danh mục cần đăng nhập lại (cookie đã bị xóa).
    assert client.get("/api/portfolio/holdings").status_code == 401
    assert _login(client).status_code == 200
    hold = client.get("/api/portfolio/holdings")
    assert hold.status_code == 200, hold.text
    data = hold.json()
    assert len(data) == 3  # TPB, VIB (đang giữ) + HPG (đã bán hết, có lãi/lỗ đã TH)
    tpb = next(h for h in data if h["ticker"] == "TPB")
    assert tpb["quantity"] == 1200 and tpb["avg_price"] == 14544
    assert tpb["market_price"] == 14450 and tpb["account_no"] == "0001M18951"
    assert tpb["realized_pnl"] == -2391
    hpg = next(h for h in data if h["ticker"] == "HPG")
    assert hpg["quantity"] == 0 and hpg["realized_pnl"] == 150000


def test_import_replaces_previous(client):
    assert _register(client, email="r@fund.vn").status_code == 201
    token = client.post("/api/portfolio/import-token").json()["token"]
    h = {"Authorization": f"Bearer {token}"}

    client.post("/api/portfolio/import",
                json={"holdings": [{"ticker": "AAA", "qty": 10, "avgPrice": 1000}]}, headers=h)
    client.post("/api/portfolio/import",
                json={"holdings": [{"ticker": "BBB", "qty": 20, "avgPrice": 2000}]}, headers=h)

    got = client.get("/api/portfolio/holdings").json()
    assert [x["ticker"] for x in got] == ["BBB"]  # lưu đè, không dồn thêm


def test_import_lots_and_read(client):
    assert _register(client, email="lot@invest.vn").status_code == 201
    token = client.post("/api/portfolio/import-token").json()["token"]
    h = {"Authorization": f"Bearer {token}"}
    body = {
        "source": "TCBS", "account": "0001M18951",
        "lots": [
            {"ticker": "tpb", "side": "buy", "qty": 100, "price": 14750, "txdate": "2026-08-24", "orderId": "A1"},
            {"ticker": "TPB", "side": "sell", "qty": 100, "price": 14550, "txdate": "2026-08-26", "orderId": "A2"},
        ],
    }
    imp = client.post("/api/portfolio/import-lots", json=body, headers=h)
    assert imp.status_code == 200, imp.text
    assert imp.json()["imported"] == 2 and imp.json()["tickers"] == ["TPB"]

    assert client.get("/api/portfolio/lots").status_code == 200
    got = client.get("/api/portfolio/lots").json()
    assert len(got) == 2
    buy = next(l for l in got if l["side"] == "buy")
    assert buy["ticker"] == "TPB" and buy["price"] == 14750 and buy["quantity"] == 100
    sell = next(l for l in got if l["side"] == "sell")
    assert sell["price"] == 14550


def test_import_rejects_foreign_token_secret(client):
    #  Token bịa (không ký bằng khóa hệ thống) → coi như không có, rơi về 401.
    assert _register(client, email="x@stox.vn").status_code == 201
    client.cookies.clear()
    bad = client.post("/api/portfolio/import",
                      json={"holdings": [{"ticker": "FPT", "qty": 1}]},
                      headers={"Authorization": "Bearer not-a-real-token"})
    assert bad.status_code == 401
