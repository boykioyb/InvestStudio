"""Test danh sách theo dõi: CRUD, chuẩn hóa mã, và cô lập giữa người dùng."""
from __future__ import annotations


def _register(client, email="u@b.com"):
    return client.post("/api/auth/register", json={"email": email, "password": "secret123"})


def test_requires_auth(client):
    assert client.get("/api/watchlist").status_code == 401
    assert client.post("/api/watchlist", json={"ticker": "FPT"}).status_code == 401


def test_add_list_patch_delete(client):
    _register(client)
    add = client.post("/api/watchlist", json={"ticker": "fpt", "note": "thử"})
    assert add.status_code == 201, add.text
    item = add.json()
    assert item["ticker"] == "FPT"  # chuẩn hóa hoa

    dup = client.post("/api/watchlist", json={"ticker": "FPT"})
    assert dup.status_code == 409

    lst = client.get("/api/watchlist")
    assert lst.status_code == 200 and len(lst.json()) == 1

    patch = client.patch(f"/api/watchlist/{item['id']}",
                         json={"target_price": 120.5, "target_score": 80})
    assert patch.status_code == 200
    assert patch.json()["target_price"] == 120.5 and patch.json()["target_score"] == 80

    dele = client.delete(f"/api/watchlist/{item['id']}")
    assert dele.status_code == 204
    assert client.get("/api/watchlist").json() == []


def test_invalid_ticker_422(client):
    _register(client)
    assert client.post("/api/watchlist", json={"ticker": "FP-T"}).status_code == 422


def test_isolation_between_users(client):
    #  Người A tạo một mục.
    _register(client, email="a@b.com")
    item = client.post("/api/watchlist", json={"ticker": "FPT"}).json()
    client.post("/api/auth/logout")

    #  Người B không thấy và không xóa được mục của A.
    _register(client, email="b@b.com")
    assert client.get("/api/watchlist").json() == []
    assert client.delete(f"/api/watchlist/{item['id']}").status_code == 404
