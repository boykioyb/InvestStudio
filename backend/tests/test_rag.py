"""Test tầng RAG KHÔNG gọi Gemini thật.

Kho vector (`store`) test bằng vector giả 768 chiều. Luồng hỏi–đáp (`chat`) test
bằng cách monkeypatch hàm nhúng + sinh câu trả lời — chỉ kiểm phần lắp ghép ngữ
cảnh và trích nguồn, không phụ thuộc mạng.
"""
from __future__ import annotations


def _vec(seed: int) -> list[float]:
    """Vector 768 chiều tất định theo seed (đủ để phân biệt khi tìm cosine)."""
    return [((i * seed) % 7) * 0.01 for i in range(768)]


def _doc(source_key, ticker, content, vec, doc_type="summary"):
    return {"source_key": source_key, "doc_type": doc_type, "ticker": ticker,
            "title": f"{ticker}", "content": content, "meta": {}, "embedding": vec}


def test_upsert_idempotent_and_search(db):
    from app.services.rag import store
    vec = _vec(1)
    assert store.upsert_documents(db, [_doc("summary:FPT", "FPT", "ROE cao", vec)]) == 1

    hits = store.search(db, vec, top_k=3)
    assert hits and hits[0][0].ticker == "FPT"
    assert hits[0][1] > 0.99  # cosine gần 1.0 với chính nó

    #  Upsert lại cùng source_key → GHI ĐÈ, không nhân bản.
    store.upsert_documents(db, [_doc("summary:FPT", "FPT", "đã cập nhật", vec)])
    docs, tickers = store.stats(db)
    assert docs == 1 and tickers == 1


def test_search_filter_by_ticker(db):
    from app.services.rag import store
    store.upsert_documents(db, [
        _doc("s:FPT", "FPT", "a", _vec(1)),
        _doc("s:VCB", "VCB", "b", _vec(2)),
    ])
    hits = store.search(db, _vec(1), top_k=5, ticker="VCB")
    assert hits and all(doc.ticker == "VCB" for doc, _ in hits)


def test_chat_answers_from_context(db, monkeypatch):
    from app.services.rag import chat, store
    store.upsert_documents(db, [
        _doc("news:FPT", "FPT", "FPT chia cổ tức 20%", _vec(3), doc_type="news")])

    #  Nhúng câu hỏi trả về đúng vector của tài liệu → nó là hit số 1.
    monkeypatch.setattr(chat, "embed_texts", lambda texts, is_query=False: [_vec(3)])
    monkeypatch.setattr(chat, "generate_answer", lambda system, prompt: "Theo dữ liệu: cổ tức 20%.")

    resp = chat.answer_question(db, "FPT có tin gì?")
    assert "cổ tức" in resp.answer
    assert resp.citations and resp.citations[0].ticker == "FPT"
    assert "khuyến nghị đầu tư" in resp.note.lower()


def test_chat_empty_store_says_no_data(db, monkeypatch):
    from app.services.rag import chat
    monkeypatch.setattr(chat, "embed_texts", lambda texts, is_query=False: [[0.0] * 768])
    resp = chat.answer_question(db, "hỏi gì đó")
    assert resp.citations == []
    assert "lập chỉ mục" in resp.answer.lower()
